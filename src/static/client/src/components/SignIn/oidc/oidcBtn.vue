<script setup async>
import axios from "axios";
import {ref} from "vue";

const props = defineProps(['provider', 'name'])
const providerAvailable = ref(false)
const providerConfiguration = ref({})
const params = new URLSearchParams({
	client_id: props.provider.client_id,
	redirect_uri: window.location.protocol + '//' + window.location.host + window.location.pathname,
	response_type: 'code',
	state: props.name,
	scope: 'openid email profile'
}).toString()
const authUrl = ref(undefined)

try{
	const getProviderConfiguration = await axios(`${props.provider.issuer}/.well-known/openid-configuration`)
	console.log(getProviderConfiguration)
	providerAvailable.value = true
	providerConfiguration.value = getProviderConfiguration.data
	console.log(providerConfiguration.value)
	authUrl.value = new URL(providerConfiguration.value.authorization_endpoint)
	authUrl.value.search = params
} catch (error){
	console.log("Provider not available", props.provider)
}
</script>

<template>
	<a class="btn btn-sm btn-outline-body rounded-3"
	   v-if="providerAvailable"
	   :href="authUrl"
	   style="flex: 1 1 0px;" >
		{{ name }}
	</a>
</template>

<style scoped>

</style>