import axios from "axios";

export const requestURl = (url) => {
	if (import.meta.env.MODE === 'development') {
		return '/client' + url;
	}
	return `./.${url}`;
}

export const axiosPost = async (URL, body = {}) => {
	try{
		const res = await axios.post(requestURl(URL), body)
		return res.data
	} catch (error){
		console.log(error)
		return undefined
	}
}

export const axiosGet = async (URL, query = {}) => {
	try{
		const res = await axios.get(requestURl(URL), query)
		return res.data
	} catch (error){
		console.log(error)
		return undefined
	}
}