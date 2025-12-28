<script setup lang="ts">
import { ref, reactive } from "vue"
import LocaleText from "@/components/text/localeText.vue";
import OidcSettings from "@/components/clientComponents/clientSettingComponents/oidcSettings.vue";
import { fetchGet, fetchPost } from "@/utilities/fetch.js"
const emits = defineEmits(['close'])
import { DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore"
const dashboardConfigurationStore = DashboardConfigurationStore()
const loading = ref(false)
const values = reactive({
	enableClients: dashboardConfigurationStore.Configuration.Clients.enable
})

const toggling = ref(false)
const updateSettings = async (key: string) => {
	toggling.value = true
	await fetchPost("/api/updateDashboardConfigurationItem", {
		section: "Clients",
		key: key,
		value: dashboardConfigurationStore.Configuration.Clients[key]
	}, async (res) => {
		await dashboardConfigurationStore.getConfiguration()
		toggling.value = false
	})
}
</script>

<template>
<div class="position-absolute w-100 h-100 top-0 start-0 z-1 rounded-3 d-flex p-2" style="background-color: #00000070; z-index: 9999">
	<div class="card m-auto rounded-3" style="width: 700px">
		<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-2">
			<h4 class="mb-0">
				<LocaleText t="Clients Settings"></LocaleText>
			</h4>
			<button type="button" class="btn-close ms-auto" @click="emits('close')"></button>
		</div>
		<div class="card-body px-4 d-flex gap-3 flex-column">
			<div class="d-flex align-items-center">
				<h6 class="mb-0">
					<LocaleText t="Client Side App"></LocaleText>
				</h6>
				<div class="form-check form-switch ms-auto">
					<label class="form-check-label" for="oidc_switch">
						<LocaleText :t="dashboardConfigurationStore.Configuration.Clients.enable ? 'Enabled':'Disabled'"></LocaleText>
					</label>
					<input
						:disabled="toggling"
						v-model="dashboardConfigurationStore.Configuration.Clients.enable"
						@change="updateSettings('enable')"
						class="form-check-input" type="checkbox" role="switch" id="oidc_switch">
				</div>
			</div>
			<hr>
			<div>
				<div class="d-flex align-items-center">
					<h6 class="mb-0">
						<LocaleText t="Sign Up as Local Client"></LocaleText>
					</h6>
					<div class="form-check form-switch ms-auto">
						<label class="form-check-label" for="sign_up_switch">
							<LocaleText :t="dashboardConfigurationStore.Configuration.Clients.sign_up ? 'Enabled':'Disabled'"></LocaleText>
						</label>
						<input
							:disabled="toggling"
							v-model="dashboardConfigurationStore.Configuration.Clients.sign_up"
							@change="updateSettings('sign_up')"
							class="form-check-input" type="checkbox" role="switch" id="sign_up_switch">
					</div>
				</div>
				<small class="text-muted mb-0">
					<LocaleText t="Allow clients to sign up with Email and Password"></LocaleText>
				</small>
			</div>
			<div>
				<OidcSettings mode="Client"></OidcSettings>
				<small class="text-muted mb-0">
					<LocaleText t="Allow clients to access with OpenID"></LocaleText>
				</small>
			</div>

		</div>
	</div>
</div>
</template>

<style scoped>

</style>