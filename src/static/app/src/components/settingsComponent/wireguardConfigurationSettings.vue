<script setup lang="ts">

import DashboardSettingsInputWireguardConfigurationPath
	from "@/components/settingsComponent/dashboardSettingsInputWireguardConfigurationPath.vue";
import DashboardSettingsWireguardConfigurationAutostart
	from "@/components/settingsComponent/dashboardSettingsWireguardConfigurationAutostart.vue";
import DashboardWireguardConfigurationTracking
	from "@/components/settingsComponent/dashboardWireguardConfigurationTracking.vue";
import DashboardWarpSettings
	from "@/components/settingsComponent/dashboardWarpSettings.vue";
</script>

<template>
	<div class="d-flex gap-3 flex-column" >
		<DashboardSettingsInputWireguardConfigurationPath
			targetData="wg_conf_path"
			title="Configurations Directory"
			:warning="true"
			warning-text="Remember to remove / at the end of your path. e.g /etc/wireguard"
		>
		</DashboardSettingsInputWireguardConfigurationPath>
		<DashboardSettingsWireguardConfigurationAutostart></DashboardSettingsWireguardConfigurationAutostart>
		<DashboardWireguardConfigurationTracking/>
		<DashboardWarpSettings/>
	</div>
</template>

<style scoped>

</style>