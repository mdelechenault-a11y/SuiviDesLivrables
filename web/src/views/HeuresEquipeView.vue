<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { api, ApiError, fmtDate, fmtHeures, isoDate } from '../api';

interface Ligne {
  id: number;
  date: string;
  heures: number;
  utilisateur_id: number;
  utilisateur: string;
  tache: string;
  activite: string | null;
  projet_code: string;
  projet: string;
}

const code = String(useRoute().params.filiale);
const du = ref(isoDate(new Date(Date.now() - 30 * 864e5)));
const au = ref(isoDate(new Date()));
const qui = ref(0);
const lignes = ref<Ligne[]>([]);
const erreur = ref('');

const personnes = computed(() => {
  const m = new Map<number, string>();
  lignes.value.forEach((l) => m.set(l.utilisateur_id, l.utilisateur));
  return [...m.entries()].sort((a, b) => a[1].localeCompare(b[1]));
});
const visibles = computed(() => (qui.value ? lignes.value.filter((l) => l.utilisateur_id === qui.value) : lignes.value));
const total = computed(() => visibles.value.reduce((s, l) => s + l.heures, 0));
const parPersonne = computed(() =>
  personnes.value.map(([id, nom]) => ({ id, nom, heures: lignes.value.filter((l) => l.utilisateur_id === id).reduce((s, l) => s + l.heures, 0) })),
);

async function charger() {
  erreur.value = '';
  try {
    lignes.value = await api<Ligne[]>('GET', `/api/f/${code}/pointages?du=${du.value}&au=${au.value}`);
  } catch (e) {
    erreur.value = e instanceof ApiError ? e.message : 'Chargement impossible.';
  }
}
onMounted(charger);
</script>

<template>
  <div class="page">
    <div class="top">
      <div><h1>Heures de l'équipe</h1><p>Visible uniquement par les profils autorisés (manager, directeur).</p></div>
      <div class="filters">
        <input id="du" v-model="du" type="date" aria-label="Du" @change="charger" />
        <input id="au" v-model="au" type="date" aria-label="Au" @change="charger" />
        <select id="qui" v-model.number="qui">
          <option :value="0">Toutes les personnes</option>
          <option v-for="[id, nom] in personnes" :key="id" :value="id">{{ nom }}</option>
        </select>
      </div>
    </div>
    <p v-if="erreur" class="error">{{ erreur }}</p>
    <div class="tiles">
      <div class="tile"><span class="lbl">Total</span><span class="val">{{ fmtHeures(total) }}</span><span class="sub">{{ visibles.length }} pointages</span></div>
      <div v-for="p in parPersonne.slice(0, 3)" :key="p.id" class="tile"><span class="lbl">{{ p.nom }}</span><span class="val">{{ fmtHeures(p.heures) }}</span></div>
    </div>
    <section class="panel">
      <div class="scroll">
        <table>
          <thead><tr><th>Date</th><th>Personne</th><th>Projet</th><th>Tâche</th><th>Activité</th><th class="num">Heures</th></tr></thead>
          <tbody>
            <tr v-for="l in visibles" :key="l.id">
              <td>{{ fmtDate(l.date) }}</td>
              <td>{{ l.utilisateur }}</td>
              <td><span class="mono">{{ l.projet_code }}</span> {{ l.projet }}</td>
              <td>{{ l.tache }}</td>
              <td class="muted">{{ l.activite ?? '—' }}</td>
              <td class="num">{{ fmtHeures(l.heures) }}</td>
            </tr>
            <tr v-if="!visibles.length"><td colspan="6" class="muted">Aucun pointage sur la période.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
