<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { api, fmtHeures, isoDate, lundi } from '../api';
import { peut, session } from '../session';

const route = useRoute();
const code = String(route.params.filiale);
const filiale = computed(() => session.data?.utilisateur.filiales.find((f) => f.code === code));
const semaine = ref<number | null>(null);
const taches = ref<number | null>(null);

onMounted(async () => {
  if (!peut('temps.saisir')) return;
  const du = isoDate(lundi());
  const au = isoDate(new Date(lundi().getTime() + 6 * 864e5));
  const [p, t] = await Promise.all([
    api<Array<{ heures: number }>>('GET', `/api/f/${code}/mes-pointages?du=${du}&au=${au}`),
    api<unknown[]>('GET', `/api/f/${code}/mes-taches`),
  ]);
  semaine.value = p.reduce((s, x) => s + x.heures, 0);
  taches.value = t.length;
});

const modules = [
  { nom: 'Projets, tâches et Gantt', etape: 'Étape 2' },
  { nom: 'Livrables, facturation et prévisionnel', etape: 'Étape 2' },
  { nom: 'KPI, objectifs et calendrier', etape: 'Étape 2' },
  { nom: 'CRM : opportunités et leads en tickets', etape: 'Étape 3' },
  { nom: 'Achats : commandes fournisseurs et réceptions', etape: 'Étape 3' },
  { nom: 'Bilans des affaires, bilans financiers et simulation', etape: 'Étape 3' },
];
</script>

<template>
  <div class="page">
    <div class="top">
      <div>
        <h1>Bonjour {{ session.data?.utilisateur.prenom }}</h1>
        <p>{{ filiale?.nom }}</p>
      </div>
    </div>
    <div v-if="peut('temps.saisir')" class="tiles">
      <div class="tile"><span class="lbl">Heures cette semaine</span><span class="val">{{ semaine === null ? '…' : fmtHeures(semaine) }}</span></div>
      <div class="tile"><span class="lbl">Tâches en cours</span><span class="val">{{ taches ?? '…' }}</span><span class="sub">sur les projets en cours</span></div>
      <div class="tile">
        <span class="lbl">Pointer</span>
        <RouterLink :to="`/f/${code}/heures`"><button class="primary">Saisir mes heures</button></RouterLink>
      </div>
    </div>
    <section class="panel">
      <h2>Modules à venir</h2>
      <p class="hint">Le socle (connexion, filiales, droits, heures) est en place. Les écrans de l'ancienne appli arrivent ensuite, puis les nouveaux modules.</p>
      <table>
        <tbody>
          <tr v-for="m in modules" :key="m.nom">
            <td>{{ m.nom }}</td>
            <td><span class="chip c-mut">{{ m.etape }}</span></td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>
