<script setup>

import LocaleText from "@/components/text/localeText.vue";
import ConfigurationTracking
	from "@/components/settingsComponent/dashboardWireguardConfigurationTrackingComponents/configurationTracking.vue";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {onMounted, ref, watch} from "vue";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

const store = WireguardConfigurationsStore()
const dashboardStore = DashboardConfigurationStore()
const peerTrackingStatus = ref(dashboardStore.Configuration.WireGuardConfiguration.peer_tracking)
const loaded = ref(false)
const trackingData = ref({})
onMounted(async () => {
	if (peerTrackingStatus.value){
		await loadData()
	}
})

const loadData = async () => {
	await fetchGet("/api/getPeerTrackingTableCounts", {}, (ref) => {
		if (ref.status){
			trackingData.value = ref.data
		}
		loaded.value = true
	})
}

watch(peerTrackingStatus, async (newVal) => {
	await fetchPost("/api/updateDashboardConfigurationItem", {
		section: "WireGuardConfiguration",
		key: "peer_tracking",
		value: newVal
	}, async (res) => {
		if (res.status){
			dashboardStore.newMessage("Server", newVal ? "Peer tracking enabled" : "Peer tracking disabled", "success")
			if (newVal) await loadData()
		}
	})
})
</script>

<template>
<div class="card">
	<div class="card-header d-flex align-items-center">
		<h6 class="my-2">
			<LocaleText t="Peer Tracking"></LocaleText>
		</h6>
		<div class="form-check form-switch ms-auto">
			<input class="form-check-input"
				   v-model="peerTrackingStatus"
				   type="checkbox" role="switch" id="peerTrackingStatus">
			<label class="form-check-label" for="peerTrackingStatus">
				<LocaleText t="Enabled" v-if="peerTrackingStatus"></LocaleText>
				<LocaleText t="Disabled" v-else></LocaleText>
			</label>
		</div>
	</div>
	<div class="card-body d-flex flex-column gap-3" v-if="peerTrackingStatus">
		<template v-if="!loaded">
			<div class="spinner-border text-body m-auto"></div>
		</template>
		<template v-else>
			<ConfigurationTracking :configuration="configuration"
								   :trackingData="trackingData"
								   v-for="configuration in store.Configurations"/>
		</template>
	</div>
</div>
</template>

<style scoped>

</style>