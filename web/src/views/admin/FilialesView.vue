<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { api, ApiError, fmtEuros } from '../../api';
import { chargerSession } from '../../session';

interface Filiale {
  id: number;
  code: string;
  nom: string;
  db_name: string;
  objectif_point_mort: number;
  objectif_1: number;
  objectif_2: number;
  actif: boolean;
}

const filiales = ref<Filiale[]>([]);
const form = reactive({ code: '', nom: '' });
const edition = ref<Filiale | null>(null);
const erreur = ref('');
const message = ref('');
const envoi = ref(false);

async function charger() {
  filiales.value = await api<Filiale[]>('GET', '/api/admin/filiales');
}

async function creer() {
  erreur.value = message.value = '';
  envoi.value = true;
  try {
    const f = await api<{ code: string; db_name: string }>('POST', '/api/admin/filiales', form);
    message.value = `Filiale ${f.code} créée, avec sa base ${f.db_name}.`;
    form.code = form.nom = '';
    await Promise.all([charger(), chargerSession()]);
  } catch (e) {
    erreur.value = e instanceof ApiError ? [e.message, ...(e.details ?? [])].join(' ') : 'Création impossible.';
  } finally {
    envoi.value = false;
  }
}

async function enregistrer() {
  if (!edition.value) return;
  const f = edition.value;
  erreur.value = message.value = '';
  try {
    await api('PATCH', `/api/admin/filiales/${f.id}`, {
      nom: f.nom,
      objectif_point_mort: Number(f.objectif_point_mort),
      objectif_1: Number(f.objectif_1),
      objectif_2: Number(f.objectif_2),
      actif: f.actif,
    });
    message.value = `Filiale ${f.code} enregistrée.`;
    edition.value = null;
    await Promise.all([charger(), chargerSession()]);
  } catch (e) {
    erreur.value = e instanceof ApiError ? e.message : 'Enregistrement impossible.';
  }
}

onMounted(charger);
</script>

<template>
  <div class="page">
    <div class="top"><div><h1>Filiales</h1><p>Chaque filiale a sa propre base de données. Les objectifs servent aux KPI.</p></div></div>

    <section class="panel">
      <h2>Nouvelle filiale</h2>
      <form class="form" @submit.prevent="creer">
        <label>Code<input id="f-code" v-model="form.code" required pattern="[A-Za-z0-9_]{2,20}" placeholder="ex. NORD" /></label>
        <label>Nom<input id="f-nom" v-model="form.nom" required placeholder="ex. Filiale Nord" /></label>
        <div class="actions"><button class="primary" :disabled="envoi">{{ envoi ? 'Création de la base…' : 'Créer la filiale' }}</button></div>
      </form>
      <p class="hint">Le code ne peut plus changer : il sert à nommer la base et les adresses des pages.</p>
      <p v-if="message" class="success">{{ message }}</p>
      <p v-if="erreur" class="error">{{ erreur }}</p>
    </section>

    <section class="panel">
      <div class="scroll">
        <table>
          <thead><tr><th>Code</th><th>Nom</th><th>Base</th><th class="num">Point mort</th><th class="num">Objectif 1</th><th class="num">Objectif 2</th><th>État</th><th></th></tr></thead>
          <tbody>
            <template v-for="f in filiales" :key="f.id">
              <tr v-if="edition?.id !== f.id">
                <td class="mono">{{ f.code }}</td>
                <td>{{ f.nom }}</td>
                <td class="mono muted">{{ f.db_name }}</td>
                <td class="num">{{ fmtEuros(f.objectif_point_mort) }}</td>
                <td class="num">{{ fmtEuros(f.objectif_1) }}</td>
                <td class="num">{{ fmtEuros(f.objectif_2) }}</td>
                <td><span :class="['chip', f.actif ? 'c-ok' : 'c-mut']">{{ f.actif ? 'Active' : 'Inactive' }}</span></td>
                <td><button class="ghost" @click="edition = { ...f }">Modifier</button></td>
              </tr>
              <tr v-else>
                <td class="mono">{{ f.code }}</td>
                <td><input v-model="edition.nom" aria-label="Nom" /></td>
                <td class="mono muted">{{ f.db_name }}</td>
                <td><input v-model.number="edition.objectif_point_mort" type="number" min="0" step="1000" aria-label="Point mort" /></td>
                <td><input v-model.number="edition.objectif_1" type="number" min="0" step="1000" aria-label="Objectif 1" /></td>
                <td><input v-model.number="edition.objectif_2" type="number" min="0" step="1000" aria-label="Objectif 2" /></td>
                <td><label class="checks"><input v-model="edition.actif" type="checkbox" /> Active</label></td>
                <td style="white-space: nowrap"><button class="primary" @click="enregistrer">Enregistrer</button> <button class="ghost" @click="edition = null">Annuler</button></td>
              </tr>
            </template>
            <tr v-if="!filiales.length"><td colspan="8" class="muted">Aucune filiale pour l'instant.</td></tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
