<script setup lang="ts">
import { peut } from '../session';
</script>

<template>
  <div class="page">
    <div class="top"><div><h1>Bienvenue</h1><p>Aucune filiale ne vous est encore attribuée.</p></div></div>
    <section class="panel">
      <template v-if="peut('admin.filiales')">
        <h2>Pour commencer</h2>
        <p class="hint">Créez une première filiale : l'appli lui crée sa propre base de données. Ajoutez ensuite les utilisateurs et rattachez-les à leur filiale.</p>
        <div class="filters">
          <RouterLink to="/admin/filiales"><button class="primary">Créer une filiale</button></RouterLink>
          <RouterLink to="/admin/utilisateurs"><button>Gérer les utilisateurs</button></RouterLink>
        </div>
      </template>
      <p v-else class="hint">Demandez à un administrateur de vous rattacher à votre filiale.</p>
    </section>
  </div>
</template>
