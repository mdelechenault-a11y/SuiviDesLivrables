<script setup lang="ts">
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api, ApiError, type Session } from '../api';
import { session } from '../session';

const route = useRoute();
const router = useRouter();
const identifiant = ref('');
const motDePasse = ref('');
const erreur = ref(route.query.expire ? 'Votre session a expiré. Reconnectez-vous.' : '');
const envoi = ref(false);

async function connecter() {
  erreur.value = '';
  envoi.value = true;
  try {
    session.data = await api<Session>('POST', '/api/auth/login', { identifiant: identifiant.value, motDePasse: motDePasse.value });
    const suite = typeof route.query.suite === 'string' && route.query.suite.startsWith('/') ? route.query.suite : '/';
    router.replace(suite);
  } catch (e) {
    erreur.value = e instanceof ApiError ? e.message : 'Le serveur ne répond pas.';
    motDePasse.value = '';
  } finally {
    envoi.value = false;
  }
}
</script>

<template>
  <div class="wrap">
    <form class="card" @submit.prevent="connecter">
      <div>
        <h1>Suivi des Livrables</h1>
        <p class="muted">Connectez-vous avec votre compte Windows habituel.</p>
      </div>
      <label class="field">
        Identifiant
        <input id="identifiant" v-model="identifiant" autocomplete="username" placeholder="ex. jdupont" required autofocus />
      </label>
      <label class="field">
        Mot de passe
        <input id="mot-de-passe" v-model="motDePasse" type="password" autocomplete="current-password" required />
      </label>
      <p v-if="erreur" class="error" role="alert">{{ erreur }}</p>
      <button class="primary" :disabled="envoi">{{ envoi ? 'Connexion…' : 'Se connecter' }}</button>
    </form>
  </div>
</template>

<style scoped>
.wrap { min-height: 100vh; display: grid; place-items: center; padding: 16px; background: var(--side); }
.card { width: min(380px, 100%); background: var(--surface); border-radius: 10px; padding: 24px; display: flex; flex-direction: column; gap: 14px; }
.card p { margin: 4px 0 0; }
</style>
