import axios from "axios";
import {useRouter} from "vue-router";

export const requestURl = (url) => {
	if (import.meta.env.MODE === 'development') {
		return '/client' + url;
	}
	const appPrefix = window.APP_PREFIX || '';
	return `${window.location.protocol}//${window.location.host}${appPrefix}/client${url}`;
}

// const router = useRouter()

export const axiosPost = async (URL, body = {}) => {
	try{
		const res = await axios.post(requestURl(URL), body)
		return res.data
	} catch (error){
		console.log(error)
		// if (error.status === 401){
		// 	await router.push('/signin')
		// }

		return undefined
	}
}

export const axiosGet = async (URL, query = {}) => {
	try{
		const res = await axios.get(requestURl(URL), query)
		return res.data
	} catch (error){
		console.log(error)
		// if (error.status === 401){
		// 	await router.push('/signin')
		// }
		return undefined
	}
}