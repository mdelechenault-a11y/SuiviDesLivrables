import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { chargerSession, peut, session } from './session';

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean;
    permission?: string;
    titre?: string;
  }
}

const routes: RouteRecordRaw[] = [
  { path: '/connexion', component: () => import('./views/ConnexionView.vue'), meta: { public: true, titre: 'Connexion' } },
  {
    path: '/',
    component: () => import('./components/AppLayout.vue'),
    children: [
      { path: '', component: () => import('./views/AucuneFilialeView.vue'), meta: { titre: 'Accueil' } },
      { path: 'f/:filiale', redirect: (to) => `/f/${String(to.params.filiale)}/accueil` },
      { path: 'f/:filiale/accueil', component: () => import('./views/AccueilView.vue'), meta: { titre: 'Accueil' } },
      { path: 'f/:filiale/heures', component: () => import('./views/MesHeuresView.vue'), meta: { titre: 'Mes heures', permission: 'temps.saisir' } },
      { path: 'f/:filiale/equipe', component: () => import('./views/HeuresEquipeView.vue'), meta: { titre: "Heures de l'équipe", permission: 'temps.voir_equipe' } },
      { path: 'admin/filiales', component: () => import('./views/admin/FilialesView.vue'), meta: { titre: 'Filiales', permission: 'admin.filiales' } },
      { path: 'admin/utilisateurs', component: () => import('./views/admin/UtilisateursView.vue'), meta: { titre: 'Utilisateurs', permission: 'admin.utilisateurs' } },
      { path: 'admin/droits', component: () => import('./views/admin/DroitsView.vue'), meta: { titre: 'Droits', permission: 'admin.droits' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
];

export const router = createRouter({ history: createWebHistory(), routes });

router.beforeEach(async (to) => {
  if (!session.charge) await chargerSession();
  if (to.meta.public) return true;
  if (!session.data) return { path: '/connexion', query: to.fullPath !== '/' ? { suite: to.fullPath } : {} };

  const filiales = session.data.utilisateur.filiales;
  // Page d'accueil : on ouvre directement la première filiale de l'utilisateur.
  if (to.path === '/' && filiales.length) return `/f/${filiales[0]!.code}/accueil`;
  if (to.params.filiale && !filiales.some((f) => f.code === to.params.filiale)) return '/';
  if (to.meta.permission && !peut(to.meta.permission)) return '/';
  return true;
});

router.afterEach((to) => {
  document.title = to.meta.titre ? `${to.meta.titre} · Suivi des Livrables` : 'Suivi des Livrables';
});
