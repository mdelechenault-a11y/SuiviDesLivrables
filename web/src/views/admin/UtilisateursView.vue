<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { api, ApiError } from '../../api';
import { session } from '../../session';

interface Ligne {
  id: number;
  identifiant: string;
  prenom: string;
  nom: string;
  email: string | null;
  role: string;
  actif: boolean;
  derniere_connexion: string | null;
  filiales: number[];
}
interface Filiale {
  id: number;
  code: string;
  nom: string;
}

const ROLES = ['Utilisateur', 'Chef de projet', 'Manager', 'Directeur', 'Admin'];
const local = computed(() => session.data?.modeConnexion === 'local');
const users = ref<Ligne[]>([]);
const filiales = ref<Filiale[]>([]);
const filtre = ref(0);
const erreur = ref('');
const message = ref('');
const vide = () => ({ id: 0, identifiant: '', prenom: '', nom: '', email: '', role: 'Utilisateur', filiales: [] as number[], actif: true, motDePasse: '' });
const form = reactive(vide());

const visibles = computed(() => (filtre.value ? users.value.filter((u) => u.filiales.includes(filtre.value)) : users.value));
const nomFiliale = (id: number) => filiales.value.find((f) => f.id === id)?.code ?? '?';

async function charger() {
  [users.value, filiales.value] = await Promise.all([api<Ligne[]>('GET', '/api/admin/utilisateurs'), api<Filiale[]>('GET', '/api/admin/filiales')]);
}

function editer(u: Ligne) {
  Object.assign(form, { ...u, email: u.email ?? '', motDePasse: '' });
  message.value = erreur.value = '';
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
function annuler() {
  Object.assign(form, vide());
}

async function enregistrer() {
  erreur.value = message.value = '';
  const payload = {
    prenom: form.prenom,
    nom: form.nom,
    email: form.email || null,
    role: form.role,
    filiales: form.filiales,
    ...(local.value && form.motDePasse ? { motDePasse: form.motDePasse } : {}),
  };
  try {
    if (form.id) {
      await api('PATCH', `/api/admin/utilisateurs/${form.id}`, { ...payload, actif: form.actif });
      message.value = `${form.prenom} ${form.nom} enregistré(e).`;
    } else {
      await api('POST', '/api/admin/utilisateurs', { identifiant: form.identifiant, ...payload });
      message.value = `${form.prenom} ${form.nom} peut maintenant se connecter avec l'identifiant ${form.identifiant}.`;
    }
    annuler();
    await charger();
  } catch (e) {
    erreur.value = e instanceof ApiError ? [e.message, ...(e.details ?? [])].join(' ') : 'Enregistrement impossible.';
  }
}

onMounted(charger);
</script>

<template>
  <div class="page">
    <div class="top">
      <div><h1>Utilisateurs</h1><p>{{ local ? 'Mode local : les mots de passe sont gérés ici.' : "Connexion par Active Directory : saisissez l'identifiant Windows, sans domaine." }}</p></div>
      <div class="filters">
        <select id="filtre-filiale" v-model.number="filtre" aria-label="Filtrer par filiale">
          <option :value="0">Toutes les filiales</option>
          <option v-for="f in filiales" :key="f.id" :value="f.id">{{ f.nom }}</option>
        </select>
      </div>
    </div>

    <section class="panel">
      <h2>{{ form.id ? `Modifier ${form.prenom} ${form.nom}` : 'Ajouter un utilisateur' }}</h2>
      <form class="form" @submit.prevent="enregistrer">
        <label>Identifiant Windows<input id="u-identifiant" v-model="form.identifiant" :disabled="!!form.id" required placeholder="ex. jdupont" /></label>
        <label>Prénom<input id="u-prenom" v-model="form.prenom" required /></label>
        <label>Nom<input id="u-nom" v-model="form.nom" required /></label>
        <label>E-mail<input id="u-email" v-model="form.email" type="email" /></label>
        <label>
          Rôle
          <select id="u-role" v-model="form.role" :disabled="form.id === session.data?.utilisateur.id">
            <option v-for="r in ROLES" :key="r">{{ r }}</option>
          </select>
        </label>
        <label v-if="local">Mot de passe{{ form.id ? ' (laisser vide pour garder)' : '' }}<input id="u-mdp" v-model="form.motDePasse" type="password" minlength="10" :required="!form.id" autocomplete="new-password" /></label>
        <div class="field" style="grid-column: 1 / -1">
          Filiales
          <div class="checks">
            <label v-for="f in filiales" :key="f.id"><input v-model="form.filiales" type="checkbox" :value="f.id" /> {{ f.nom }}</label>
            <span v-if="!filiales.length" class="muted">Créez d'abord une filiale.</span>
          </div>
        </div>
        <label v-if="form.id" class="checks" style="flex-direction: row"><input v-model="form.actif" type="checkbox" :disabled="form.id === session.data?.utilisateur.id" /> Compte actif</label>
        <div class="actions">
          <button class="primary">{{ form.id ? 'Enregistrer' : 'Ajouter' }}</button>
          <button v-if="form.id" type="button" @click="annuler">Annuler</button>
        </div>
      </form>
      <p v-if="message" class="success">{{ message }}</p>
      <p v-if="erreur" class="error">{{ erreur }}</p>
    </section>

    <section class="panel">
      <div class="scroll">
        <table>
          <thead><tr><th>Nom</th><th>Identifiant</th><th>E-mail</th><th>Rôle</th><th>Filiales</th><th>Dernière connexion</th><th></th></tr></thead>
          <tbody>
            <tr v-for="u in visibles" :key="u.id" :class="{ muted: !u.actif }">
              <td>{{ u.prenom }} {{ u.nom }} <span v-if="!u.actif" class="chip c-mut">Désactivé</span></td>
              <td class="mono">{{ u.identifiant }}</td>
              <td>{{ u.email ?? '—' }}</td>
              <td><span :class="['chip', u.role === 'Admin' ? 'c-crit' : u.role === 'Directeur' || u.role === 'Manager' ? 'c-warn' : u.role === 'Chef de projet' ? 'c-acc' : 'c-mut']">{{ u.role }}</span></td>
              <td>{{ u.role === 'Admin' && !u.filiales.length ? 'Toutes' : u.filiales.map(nomFiliale).join(', ') || '—' }}</td>
              <td class="muted">{{ u.derniere_connexion ? new Date(u.derniere_connexion.replace(' ', 'T') + 'Z').toLocaleString('fr-FR') : 'Jamais' }}</td>
              <td><button class="ghost" @click="editer(u)">Modifier</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
