<script>
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import PeersDefaultSettingsInput from "@/components/settingsComponent/peersDefaultSettingsInput.vue";
import AccountSettingsInputUsername from "@/components/settingsComponent/accountSettingsInputUsername.vue";
import AccountSettingsInputPassword from "@/components/settingsComponent/accountSettingsInputPassword.vue";
import DashboardSettingsInputWireguardConfigurationPath
	from "@/components/settingsComponent/dashboardSettingsInputWireguardConfigurationPath.vue";
import DashboardTheme from "@/components/settingsComponent/dashboardTheme.vue";
import DashboardSettingsInputIPAddressAndPort
	from "@/components/settingsComponent/dashboardSettingsInputIPAddressAndPort.vue";
import DashboardAPIKeys from "@/components/settingsComponent/dashboardAPIKeys.vue";
import AccountSettingsMFA from "@/components/settingsComponent/accountSettingsMFA.vue";
import LocaleText from "@/components/text/localeText.vue";
import DashboardLanguage from "@/components/settingsComponent/dashboardLanguage.vue";
import DashboardIPPortInput from "@/components/settingsComponent/dashboardIPPortInput.vue";
import DashboardSettingsWireguardConfigurationAutostart
	from "@/components/settingsComponent/dashboardSettingsWireguardConfigurationAutostart.vue";
import DashboardEmailSettings from "@/components/settingsComponent/dashboardEmailSettings.vue";

export default {
	name: "settings",
	components: {
		DashboardEmailSettings,
		DashboardSettingsWireguardConfigurationAutostart,
		DashboardIPPortInput,
		DashboardLanguage,
		LocaleText,
		AccountSettingsMFA,
		DashboardAPIKeys,
		DashboardSettingsInputIPAddressAndPort,
		DashboardTheme,
		DashboardSettingsInputWireguardConfigurationPath,
		AccountSettingsInputPassword, AccountSettingsInputUsername, PeersDefaultSettingsInput},
	setup(){
		const dashboardConfigurationStore = DashboardConfigurationStore()
		return {dashboardConfigurationStore}
	},
	data(){
		return{
			activeTab: "WGDashboard",
			tabs: [
				{
					id: "",
					title: "WGDashboard Settings"
				},
				{
					id: "peers_settings",
					title: "Peers Settings"
				},
				{
					id: "wireguard_settings",
					title: "WireGuard Configuration Settings"
				},
				{
					id: "health_monitor",
					title: "Peer Health Monitor"
				}
			]
		}
	}
}
</script>

<template>
	<div class="mt-md-5 mt-3 text-body mb-3">
		<div class="container-md d-flex flex-column gap-3">
			<div class="border-bottom pb-3">
				<ul class="nav nav-pills nav-justified align-items-center gap-2">
					<li class="nav-item" v-for="t in this.tabs">
						<RouterLink
							:to="{name: t.title}"
							class="nav-link rounded-3"
						   exact-active-class="active"
						   role="button">
							<h6 class="my-2">
								<LocaleText :t="t.title"></LocaleText>
							</h6>
						</RouterLink>
					</li>
				</ul>
			</div>
			<RouterView></RouterView>
		</div>
	</div>
</template>

<style scoped>

</style>