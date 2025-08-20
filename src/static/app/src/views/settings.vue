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
					id: "WGDashboard",
					title: "WGDashboard Settings"
				},
				{
					id: "Peers",
					title: "Peers Settings"
				},
				{
					id: "WireGuardConfiguration",
					title: "WireGuard Configuration Settings"
				}
			]
		}
	}
}
</script>

<template>
	<div class="mt-md-5 mt-3 text-body mb-3">
		<div class="container-md d-flex flex-column gap-4">
			<div>
				<ul class="nav nav-pills nav-justified align-items-center gap-2">
					<li class="nav-item" v-for="t in this.tabs">
						<a class="nav-link rounded-3"
						   @click="this.activeTab = t.id"
						   :class="{active: this.activeTab === t.id}"
						   role="button">
							<h6 class="my-2">
								<LocaleText :t="t.title"></LocaleText>
							</h6>
						</a>
					</li>
				</ul>
				<hr>
				<div>
					<Transition name="fade2" mode="out-in">
						<div class="d-flex gap-3 flex-column" v-if="activeTab === 'WireGuardConfiguration'">
							<DashboardSettingsInputWireguardConfigurationPath
								targetData="wg_conf_path"
								title="Configurations Directory"
								:warning="true"
								warning-text="Remember to remove / at the end of your path. e.g /etc/wireguard"
							>
							</DashboardSettingsInputWireguardConfigurationPath>
							<DashboardSettingsWireguardConfigurationAutostart></DashboardSettingsWireguardConfigurationAutostart>
						</div>
						<div class="d-flex gap-3 flex-column" v-else-if="activeTab === 'Peers'">
							<div class="card rounded-3">
								<div class="card-header">
									<h6 class="my-2">
										<LocaleText t="Peer Default Settings"></LocaleText>
									</h6>
								</div>
								<div class="card-body">
									<div>
										<PeersDefaultSettingsInput
											targetData="peer_global_dns" title="DNS"></PeersDefaultSettingsInput>
										<PeersDefaultSettingsInput
											targetData="peer_endpoint_allowed_ip" title="Endpoint Allowed IPs"></PeersDefaultSettingsInput>
										<PeersDefaultSettingsInput
											targetData="peer_mtu" title="MTU"></PeersDefaultSettingsInput>
										<PeersDefaultSettingsInput
											targetData="peer_keep_alive" title="Persistent Keepalive"></PeersDefaultSettingsInput>
										<PeersDefaultSettingsInput
											targetData="remote_endpoint" title="Peer Remote Endpoint"
											:warning="true" warningText="This will be changed globally, and will be apply to all peer's QR code and configuration file."
										></PeersDefaultSettingsInput>
									</div>
								</div>
							</div>
						</div>
						<div class="d-flex gap-3 flex-column" v-else-if="activeTab === 'WGDashboard'">
							<div class="card rounded-3">
								<div class="card-header">
									<h6 class="my-2">
										<LocaleText t="Appearance"></LocaleText>
									</h6>
								</div>
								<div class="card-body">
									<div class="row g-2">
										<div class="col-sm">
											<DashboardTheme></DashboardTheme>
										</div>
										<div class="col-sm">
											<DashboardLanguage></DashboardLanguage>
										</div>
									</div>
								</div>
							</div>
							<div class="card">
								<div class="card-header">
									<h6 class="my-2">
										<LocaleText t="Dashboard IP Address & Listen Port"></LocaleText>
									</h6>
								</div>
								<div class="card-body">
									<DashboardIPPortInput></DashboardIPPortInput>
								</div>
							</div>
							<div class="card">
								<div class="card-header">
									<h6 class="my-2">
										<LocaleText t="Account Settings"></LocaleText>
									</h6>
								</div>
								<div class="card-body d-flex flex-column gap-3">
									<div>
										<AccountSettingsInputUsername targetData="username"
										                              title="Username"
										></AccountSettingsInputUsername>
									</div>
									<hr>
									<div>
										<AccountSettingsInputPassword
											targetData="password">
										</AccountSettingsInputPassword>
									</div>
								</div>
							</div>
							<div class="card">
								<div class="card-header">
									<h6 class="my-2">
										<LocaleText t="Multi-Factor Authentication (MFA)"></LocaleText>
									</h6>
								</div>
								<div class="card-body">
									<AccountSettingsMFA v-if="!this.dashboardConfigurationStore.getActiveCrossServer()"></AccountSettingsMFA>
								</div>
							</div>
							<DashboardAPIKeys></DashboardAPIKeys>
							<DashboardEmailSettings></DashboardEmailSettings>
						</div>
					</Transition>
					
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>