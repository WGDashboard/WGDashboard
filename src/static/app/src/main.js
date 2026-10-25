import './css/dashboard.css'
import 'bootstrap/dist/css/bootstrap.css'
import 'bootstrap/dist/js/bootstrap.js'
import 'bootstrap-icons/font/bootstrap-icons.css'
import 'animate.css/animate.css'
import '@vuepic/vue-datepicker/dist/main.css'
import {createApp, markRaw} from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

const params = new URLSearchParams(window.location.search)
const state = params.get('state')
const code = params.get('code')

if (state && code) {
	window.history.replaceState({}, '', window.location.pathname);
	console.log('After replaceState:', window.location.href);
}




const initApp = async () => {
	const { default: router } = await import('./router/router.js')
	const app = createApp(App)

	app.use(router)
	const pinia = createPinia();
	pinia.use(piniaPluginPersistedstate)
	pinia.use(({ store }) => {
		store.$router = markRaw(router)
	})


	app.use(pinia)
	app.mount('#app')
	console.log('After router import:', window.location.href)
}

export const getUrl = (url) => {
	if (import.meta.env.MODE === 'development') {
		return url;
	}
	return `./.${url}`;
}

if (state && code){
	await fetch(getUrl('/api/oidc/authenticate'), {
		method: "POST",
		headers: {
			'content-type': 'application/json'
		},
		body: JSON.stringify({
			provider: state,
			code: code,
			redirect_uri: window.location.protocol + '//' + window.location.host + window.location.pathname
		})
	}).then(res => res.json()).then( async (res) => {
		if (res.status){
			window.location.replace(window.location.protocol + '//' + window.location.host + window.location.pathname)
		}else{
			await initApp()
			const store = DashboardConfigurationStore()
			store.newMessage('Server OIDC', res.message, 'danger')
		}
	})
}else{
	await initApp()
}
