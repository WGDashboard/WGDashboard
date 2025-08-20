import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from "@/router/router.js";
import {createPinia} from "pinia";

import 'bootstrap/dist/js/bootstrap.bundle.js'
import {axiosPost} from "@/utilities/request.js";

const params = new URLSearchParams(window.location.search)
const state = params.get('state')
const code = params.get('code')

const initApp = () => {
	const app = createApp(App)
	app.use(createPinia())
	app.use(router)
	app.mount("#app")
}

function removeSearchString() {
	let url = new URL(window.location.href);
	url.search = ''; // Remove all query parameters
	history.replaceState({}, document.title, url.toString());
}

if (state && code){
	axiosPost("/api/signin/oidc", {
		provider: state,
		code: code,
		redirect_uri: window.location.protocol + '//' + window.location.host + window.location.pathname
	}).then(data => {
		let url = new URL(window.location.href);
		url.search = '';
		history.replaceState({}, document.title, url.toString());

		initApp()
		if (!data.status){
			const store = clientStore()
			store.newNotification(data.message, 'danger')
		}
	})
}else{
	initApp()
}





