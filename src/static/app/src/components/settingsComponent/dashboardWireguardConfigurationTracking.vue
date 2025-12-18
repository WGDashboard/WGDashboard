<script setup>

import LocaleText from "@/components/text/localeText.vue";
import ConfigurationTracking
	from "@/components/settingsComponent/dashboardWireguardConfigurationTrackingComponents/configurationTracking.vue";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {onMounted, ref} from "vue";
import {fetchGet} from "@/utilities/fetch.js";

const store = WireguardConfigurationsStore()
const loaded = ref(false)
const trackingData = ref({})
onMounted(async () => {
	await fetchGet("/api/getPeerTrackingTableCounts", {}, (ref) => {
		if (ref.status){
			trackingData.value = ref.data
		}
		loaded.value = true
	})
})
</script>

<template>
<div class="card">
	<div class="card-header">
		<h6 class="my-2">
			<LocaleText t="Peer Tracking"></LocaleText>
		</h6>
	</div>
	<div class="card-body d-flex flex-column gap-3">
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