import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import {createPinia} from "pinia";

import 'bootstrap/dist/js/bootstrap.bundle.js'
import {axiosGet, axiosPost} from "@/utilities/request.js";
import {clientStore} from "@/stores/clientStore.js";

const params = new URLSearchParams(window.location.search)
const state = params.get('state')
const code = params.get('code')

if (state && code) {
	window.history.replaceState({}, '', window.location.pathname);
}

const initApp = async () => {
	debugger
	const { default: router } = await import('./router/router.js')
	const app = createApp(App)
	const serverInformation = await axiosGet("/api/serverInformation", {})
	app.use(createPinia())
	if (serverInformation){
		const store = clientStore()
		store.serverInformation = serverInformation.data;
	}
	app.use(router)
	app.mount("#app")
}

if (state && code){
	await axiosPost("/api/signin/oidc", {
		provider: state,
		code: code,
		redirect_uri: window.location.protocol + '//' + window.location.host + window.location.pathname
	}).then(async (data) => {
		if (data.status){
			window.location.replace(window.location.protocol + '//' + window.location.host + window.location.pathname)
		}else {
			await initApp()
			const store = clientStore()
			store.newNotification(data.message, 'danger')
		}
	})
}else{
	await initApp()
}





