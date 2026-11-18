<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { deconnecter, peut, session } from '../session';

const route = useRoute();
const router = useRouter();
const user = computed(() => session.data!.utilisateur);
const filiales = computed(() => user.value.filiales);
const filiale = computed(() => (typeof route.params.filiale === 'string' ? route.params.filiale : filiales.value[0]?.code));

interface Lien {
  to: string;
  label: string;
  permission?: string;
  bientot?: boolean;
}
interface Groupe {
  titre: string;
  liens: Lien[];
}

/** Menu : les modules pas encore livrés sont annoncés mais désactivés. */
const groupes = computed<Groupe[]>(() => {
  const f = filiale.value;
  const g: Groupe[] = [];
  if (f) {
    g.push({
      titre: 'Mon espace',
      liens: [
        { to: `/f/${f}/accueil`, label: 'Accueil' },
        { to: `/f/${f}/heures`, label: 'Mes heures', permission: 'temps.saisir' },
      ],
    });
    g.push({
      titre: 'Pilotage',
      liens: [
        { to: `/f/${f}/equipe`, label: "Heures de l'équipe", permission: 'temps.voir_equipe' },
        { to: '#', label: 'Projets et Gantt', permission: 'projets.voir', bientot: true },
        { to: '#', label: 'Suivi des livrables', permission: 'livrables.voir', bientot: true },
        { to: '#', label: 'KPI', permission: 'finance.voir', bientot: true },
      ],
    });
  }
  g.push({
    titre: 'Administration',
    liens: [
      { to: '/admin/utilisateurs', label: 'Utilisateurs', permission: 'admin.utilisateurs' },
      { to: '/admin/filiales', label: 'Filiales', permission: 'admin.filiales' },
      { to: '/admin/droits', label: 'Droits', permission: 'admin.droits' },
    ],
  });
  return g
    .map((x) => ({ ...x, liens: x.liens.filter((l) => !l.permission || peut(l.permission)) }))
    .filter((x) => x.liens.length);
});

function changerFiliale(e: Event) {
  const code = (e.target as HTMLSelectElement).value;
  const suffix = route.path.match(/^\/f\/[^/]+(\/.*)?$/)?.[1] ?? '/accueil';
  router.push(`/f/${code}${suffix}`);
}

async function quitter() {
  await deconnecter();
  router.push('/connexion');
}
</script>

<template>
  <div class="app">
    <aside>
      <div class="brand"><b>Suivi des Livrables</b><span>{{ user.prenom }} {{ user.nom }} · {{ user.role }}</span></div>

      <label v-if="filiales.length > 1" class="filiale">
        <span>Filiale</span>
        <select id="filiale" :value="filiale" @change="changerFiliale">
          <option v-for="f in filiales" :key="f.id" :value="f.code">{{ f.nom }}</option>
        </select>
      </label>
      <div v-else-if="filiales.length === 1" class="filiale"><span>Filiale</span><b>{{ filiales[0]!.nom }}</b></div>

      <nav>
        <div v-for="g in groupes" :key="g.titre" class="navgroup">
          <h6>{{ g.titre }}</h6>
          <template v-for="l in g.liens" :key="l.label">
            <span v-if="l.bientot" class="soon" title="Prévu à l'étape 2">{{ l.label }} <small>bientôt</small></span>
            <RouterLink v-else :to="l.to">{{ l.label }}</RouterLink>
          </template>
        </div>
      </nav>

      <button class="logout" @click="quitter">Se déconnecter</button>
    </aside>
    <main>
      <RouterView :key="route.fullPath" />
    </main>
  </div>
</template>

<style scoped>
.app { display: grid; grid-template-columns: 236px minmax(0, 1fr); min-height: 100vh; }
aside { min-width: 0; background: var(--side); color: var(--side-fg); padding: 18px 14px; display: flex; flex-direction: column; gap: 18px; }
.brand { display: flex; flex-direction: column; gap: 2px; padding: 0 8px; }
.brand b { color: #fff; font-size: 16px; }
.brand span { font-size: 12px; opacity: 0.75; }
.filiale { display: flex; flex-direction: column; gap: 4px; padding: 0 8px; font-size: 12px; }
.filiale b { color: #fff; font-weight: 600; font-size: 13px; }
.filiale select { width: 100%; }
nav { display: flex; flex-direction: column; gap: 14px; }
.navgroup { display: flex; flex-direction: column; gap: 2px; }
.navgroup h6 { margin: 0 0 4px; padding: 0 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.6; font-weight: 600; }
nav a, .soon { color: var(--side-fg); text-decoration: none; padding: 7px 10px; border-radius: 6px; display: block; }
nav a:hover { background: var(--side-active); color: #fff; }
nav a.router-link-active { background: var(--side-active); color: #fff; box-shadow: inset 3px 0 0 var(--accent); }
.soon { opacity: 0.5; cursor: default; }
.soon small { font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; margin-left: 4px; }
.logout { margin-top: auto; background: transparent; color: var(--side-fg); border-color: #ffffff2a; }
main { min-width: 0; padding: 20px max(16px, 2.2vw) 40px; }
@media (max-width: 820px) {
  .app { grid-template-columns: 1fr; }
  aside { gap: 10px; }
  nav { flex-direction: row; overflow-x: auto; gap: 4px; }
  .navgroup { flex-direction: row; gap: 2px; }
  .navgroup h6 { display: none; }
  nav a, .soon { white-space: nowrap; }
  .logout { margin-top: 0; align-self: flex-start; }
}
</style>
