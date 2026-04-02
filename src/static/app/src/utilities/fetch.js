import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import router from "@/router/router.js";
const getHeaders = () => {
	let headers = {
		"Content-Type": "application/json"
	}
	const store = DashboardConfigurationStore();
	const crossServer = store.getActiveCrossServer();
	if (crossServer){
		headers['wg-dashboard-apikey'] = crossServer.apiKey
        if (crossServer.headers){
            for (let header of Object.values(crossServer.headers)){
                if (header.key && header.value && !Object.keys(headers).includes(header.key)){
                    headers[header.key] = header.value
                }
            }
        }
	}


	return headers
}

export const getUrl = (url) => {
	const store = DashboardConfigurationStore();
	const apiKey = store.getActiveCrossServer();
	if (apiKey){
		return `${apiKey.host}${url}`
	}
	return import.meta.env.MODE === 'development' ? url 
		: `${window.location.protocol}//${(window.location.host + window.location.pathname + url).replace(/\/\//g, '/')}`
}

export const fetchGet = async (url, params=undefined, callback=undefined) => {
	const urlSearchParams = new URLSearchParams(params);
	await fetch(`${getUrl(url)}?${urlSearchParams.toString()}`, {
		headers: getHeaders()
	})
		.then((x) => {
			const store = DashboardConfigurationStore();
			if (!x.ok){
				if (x.status !== 200){
					if (x.status === 401){
						store.newMessage("WGDashboard", "Sign in session ended, please sign in again", "warning")
					}
					throw new Error(x.statusText)
				}
			}else{
				return x.json()
			}
		})
		.then(x => callback ? callback(x) : undefined).catch(x => {
			console.log("Error:", x)
			router.push({path: '/signin'})
	})
}

export const fetchPost = async (url, body, callback) => {
	await fetch(`${getUrl(url)}`, {
		headers: getHeaders(),
		method: "POST",
		body: JSON.stringify(body)
	}).then((x) => {
		const store = DashboardConfigurationStore();
		if (!x.ok){
			if (x.status !== 200){
				if (x.status === 401){
					store.newMessage("WGDashboard", "Sign in session ended, please sign in again", "warning")
				}
				throw new Error(x.statusText)
			}
		}else{
			return x.json()
		}
	}).then(x => callback ? callback(x) : undefined).catch(x => {
		console.log("Error:", x)
		router.push({path: '/signin'})
	})
}