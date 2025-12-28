import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from "@/router/router.js";
import {createPinia} from "pinia";

import 'bootstrap/dist/js/bootstrap.bundle.js'
import {axiosGet, axiosPost} from "@/utilities/request.js";
import {clientStore} from "@/stores/clientStore.js";

const params = new URLSearchParams(window.location.search)
const state = params.get('state')
const code = params.get('code')

const initApp = async () => {
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
		let url = new URL(window.location.href);
		url.search = '';
		history.replaceState({}, document.title, url.toString());

		await initApp()
		if (!data.status){
			const store = clientStore()
			store.newNotification(data.message, 'danger')
		}
	})
}else{
	await initApp()
}





