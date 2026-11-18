import { createApp } from 'vue';
import App from './App.vue';
import { router } from './router';
import { setUnauthorizedHandler } from './api';
import { session } from './session';
import './styles.css';

setUnauthorizedHandler(() => {
  session.data = null;
  if (router.currentRoute.value.path !== '/connexion') router.push({ path: '/connexion', query: { expire: '1' } });
});

createApp(App).use(router).mount('#app');
