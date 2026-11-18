<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';
import { api, ApiError, fmtDate, fmtHeures, isoDate, lundi } from '../api';

interface Tache {
  tache_id: number;
  tache: string;
  projet_code: string;
  projet: string;
  date_debut: string | null;
  date_fin: string | null;
  heures_allouees: number;
  heures_pointees: number;
}
interface Pointage {
  id: number;
  date: string;
  heures: number;
  commentaire: string | null;
  tache: string;
  projet_code: string;
}

const code = String(useRoute().params.filiale);
const taches = ref<Tache[]>([]);
const pointages = ref<Pointage[]>([]);
const debut = ref(lundi());
const erreur = ref('');
const message = ref('');
const form = reactive({ tache_id: 0, date: isoDate(new Date()), heures: 7, commentaire: '' });

const jours = computed(() => Array.from({ length: 7 }, (_, i) => isoDate(new Date(debut.value.getTime() + i * 864e5))));
const total = computed(() => pointages.value.reduce((s, p) => s + p.heures, 0));
const parJour = computed(() => jours.value.map((j) => pointages.value.filter((p) => p.date === j).reduce((s, p) => s + p.heures, 0)));

async function charger() {
  const [t, p] = await Promise.all([
    api<Tache[]>('GET', `/api/f/${code}/mes-taches`),
    api<Pointage[]>('GET', `/api/f/${code}/mes-pointages?du=${jours.value[0]}&au=${jours.value[6]}`),
  ]);
  taches.value = t;
  pointages.value = p;
  if (!form.tache_id && t[0]) {
    // Par défaut, la tâche en cours aujourd'hui.
    const today = isoDate(new Date());
    form.tache_id = (t.find((x) => x.date_debut && x.date_fin && x.date_debut <= today && today <= x.date_fin) ?? t[0]).tache_id;
  }
}

async function pointer() {
  erreur.value = '';
  message.value = '';
  try {
    await api('POST', `/api/f/${code}/pointages`, { ...form, heures: Number(form.heures), commentaire: form.commentaire || undefined });
    message.value = `${fmtHeures(Number(form.heures))} pointées le ${fmtDate(form.date)}`;
    form.commentaire = '';
    await charger();
  } catch (e) {
    erreur.value = e instanceof ApiError ? [e.message, ...(e.details ?? [])].join(' ') : 'Enregistrement impossible.';
  }
}

async function supprimer(id: number) {
  await api('DELETE', `/api/f/${code}/pointages/${id}`);
  await charger();
}

function decaler(n: number) {
  debut.value = n === 0 ? lundi() : new Date(debut.value.getTime() + n * 7 * 864e5);
  charger();
}

onMounted(charger);
</script>

<template>
  <div class="page">
    <div class="top">
      <div><h1>Mes heures</h1><p>Pointez votre temps sur les tâches qui vous sont affectées.</p></div>
    </div>

    <section class="panel">
      <h2>Pointer</h2>
      <p v-if="!taches.length" class="hint">Aucune tâche ne vous est affectée sur un projet en cours. Votre chef de projet doit vous affecter pour que vous puissiez pointer.</p>
      <form v-else class="form" @submit.prevent="pointer">
        <label style="grid-column: span 2">
          Tâche
          <select id="tache" v-model.number="form.tache_id" required>
            <option v-for="t in taches" :key="t.tache_id" :value="t.tache_id">{{ t.projet_code }} · {{ t.projet }} · {{ t.tache }}</option>
          </select>
        </label>
        <label>Date<input id="date" v-model="form.date" type="date" required /></label>
        <label>Heures<input id="heures" v-model.number="form.heures" type="number" min="0.25" max="24" step="0.25" required /></label>
        <label style="grid-column: span 2">Commentaire (facultatif)<input id="commentaire" v-model="form.commentaire" maxlength="500" /></label>
        <div class="actions"><button class="primary">Enregistrer</button></div>
      </form>
      <p v-if="message" class="success" role="status">{{ message }}</p>
      <p v-if="erreur" class="error" role="alert">{{ erreur }}</p>
    </section>

    <section class="panel">
      <div class="top">
        <h2>Semaine du {{ fmtDate(jours[0]!) }} au {{ fmtDate(jours[6]!) }} · {{ fmtHeures(total) }}</h2>
        <div class="filters">
          <button @click="decaler(-1)">← Précédente</button>
          <button @click="decaler(0)">Cette semaine</button>
          <button @click="decaler(1)">Suivante →</button>
        </div>
      </div>
      <div class="scroll">
        <table>
          <thead><tr><th v-for="(j, i) in jours" :key="j" class="num">{{ fmtDate(j) }}<br /><span :class="{ muted: !parJour[i] }">{{ parJour[i] ? fmtHeures(parJour[i]!) : '·' }}</span></th></tr></thead>
        </table>
      </div>
      <div class="scroll">
        <table>
          <thead><tr><th>Date</th><th>Projet</th><th>Tâche</th><th>Commentaire</th><th class="num">Heures</th><th></th></tr></thead>
          <tbody>
            <tr v-for="p in pointages" :key="p.id">
              <td>{{ fmtDate(p.date) }}</td>
              <td class="mono">{{ p.projet_code }}</td>
              <td>{{ p.tache }}</td>
              <td class="muted">{{ p.commentaire }}</td>
              <td class="num">{{ fmtHeures(p.heures) }}</td>
              <td><button class="ghost" @click="supprimer(p.id)">Supprimer</button></td>
            </tr>
            <tr v-if="!pointages.length"><td colspan="6" class="muted">Aucune heure pointée cette semaine.</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="taches.length" class="panel">
      <h2>Mes tâches</h2>
      <div class="scroll">
        <table>
          <thead><tr><th>Projet</th><th>Tâche</th><th>Période</th><th class="num">Alloué</th><th class="num">Pointé</th><th>Consommé</th></tr></thead>
          <tbody>
            <tr v-for="t in taches" :key="t.tache_id">
              <td><span class="mono">{{ t.projet_code }}</span> {{ t.projet }}</td>
              <td>{{ t.tache }}</td>
              <td class="muted">{{ fmtDate(t.date_debut) }} → {{ fmtDate(t.date_fin) }}</td>
              <td class="num">{{ fmtHeures(t.heures_allouees) }}</td>
              <td class="num">{{ fmtHeures(t.heures_pointees) }}</td>
              <td><div class="bar"><i :class="{ over: t.heures_pointees > t.heures_allouees }" :style="{ width: Math.min(100, (t.heures_pointees / (t.heures_allouees || 1)) * 100) + '%' }"></i></div></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
