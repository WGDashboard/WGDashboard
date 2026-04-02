<script setup>

import LocaleText from "@/components/text/localeText.vue";
import ConfigurationTracking
	from "@/components/settingsComponent/dashboardWireguardConfigurationTrackingComponents/configurationTracking.vue";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";

const store = WireguardConfigurationsStore()
</script>

<template>
<div class="card">
	<div class="card-header">
		<h6 class="my-2">
			<LocaleText t="Peer Tracking"></LocaleText>
		</h6>
	</div>
	<div class="card-body d-flex flex-column gap-3">
		<ConfigurationTracking :configuration="configuration" v-for="configuration in store.Configurations"/>
	</div>
</div>
</template>

<style scoped>

</style>