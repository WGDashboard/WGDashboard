<script setup async>
import {computed, onMounted, ref} from "vue";
import {fetchGet} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
const providers = ref([])
const oidcEnabled = ref(false)

await fetchGet("/api/oidc/providers", {}, async (res) => {
	if (res.status){
		await Promise.all(Object.entries(res.data).map(([key, value]) => {
			return fetch(`${value.issuer}/.well-known/openid-configuration`).then((res) => {
				providers.value.push({
					Provider: key,
					ProviderInfo: value
				})
			}).catch(() => {
				console.log("Failed to request " + key)
			})
		}))
		oidcEnabled.value = providers.value.length > 0
	}
})
console.log(providers.value)
const oidcUrl = (provider) => {
	const params = new URLSearchParams({
		client_id: provider.ProviderInfo.client_id,
		redirect_uri: window.location.protocol + '//' + window.location.host + window.location.pathname,
		response_type: 'code',
		state: provider.Provider,
		scope: 'openid email profile'
	})
	console.log(params.entries())
	const url = new URL(provider.ProviderInfo.openid_configuration.authorization_endpoint)
	url.search = params.toString()

	return url
}

</script>

<template>
	<div>
		<div v-if="oidcEnabled">
			<hr class="mb-4"/>
			<div class="d-flex gap-2">
				<a class="btn bg-body border w-100 rounded-3"
				   :href="oidcUrl(provider)"
				   v-for="provider in providers" style="flex: 1 1 0;">
					<LocaleText :t="'Sign In With ' + provider.Provider"/>
				</a>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>