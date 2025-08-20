<script setup lang="ts">
import {ref} from "vue"
import LocaleText from "@/components/text/localeText.vue";
import { fetchGet } from "@/utilities/fetch.js"
import { DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore"

const props = defineProps(['mode'])
const dashboardConfigurationStore = DashboardConfigurationStore()
const oidcStatus = ref(false)
const oidcStatusLoading = ref(false)

const getStatus = async () => {
	await fetchGet("/api/oidc/status", {
		mode: props.mode
	}, (res) => {
		oidcStatus.value = res.data
		oidcStatusLoading.value = false
	})
}
await getStatus()
const toggle = async () => {
	oidcStatusLoading.value = true
	await fetchGet('/api/oidc/toggle', {
		mode: props.mode
	}, (res) => {
		if (!res.status){
			oidcStatus.value = !oidcStatus.value
			dashboardConfigurationStore.newMessage("Server", res.message, "danger")
		}
		oidcStatusLoading.value = false
	})
}
</script>

<template>
<div class="d-flex flex-column gap-2">
	<div class="d-flex align-items-center">
		<h6 class="mb-0">
			<LocaleText t="OpenID Connect (OIDC)"></LocaleText>
		</h6>
		<div class="form-check form-switch ms-auto">
			<label class="form-check-label" for="oidc_switch">
				<LocaleText :t="oidcStatus ? 'Enabled':'Disabled'"></LocaleText>
			</label>
			<input
				:disabled="oidcStatusLoading"
				v-model="oidcStatus"
				@change="toggle()"
				class="form-check-input" type="checkbox" role="switch" id="oidc_switch">
		</div>
	</div>
	<div>
		<div class="alert alert-dark rounded-3 mb-0">
			<LocaleText t="Due to security reason, in order to edit OIDC configuration, you will need to edit "></LocaleText>
			<code>wg-dashboard-oidc-providers.json</code> <LocaleText t="directly, then restart WGDashboard to apply the latest settings."></LocaleText>
		</div>
	</div>
</div>
</template>

<style scoped>

</style>