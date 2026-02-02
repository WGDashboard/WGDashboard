<script setup lang="ts">
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

import LocaleText from "@/components/text/localeText.vue";
import DashboardLanguage from "@/components/settingsComponent/dashboardLanguage.vue";
import AccountSettingsInputPassword from "@/components/settingsComponent/accountSettingsInputPassword.vue";
import DashboardTheme from "@/components/settingsComponent/dashboardTheme.vue";
import DashboardAPIKeys from "@/components/settingsComponent/dashboardAPIKeys.vue";
import DashboardIPPortInput from "@/components/settingsComponent/dashboardIPPortInput.vue";
import AccountSettingsMFA from "@/components/settingsComponent/accountSettingsMFA.vue";
import AccountSettingsInputUsername from "@/components/settingsComponent/accountSettingsInputUsername.vue";
import DashboardEmailSettings from "@/components/settingsComponent/dashboardEmailSettings.vue";
import DashboardWebHooks from "@/components/settingsComponent/dashboardWebHooks.vue";
import DashboardAdminUsers from "@/components/settingsComponent/dashboardAdminUsers.vue";

const dashboardConfigurationStore = DashboardConfigurationStore()

</script>

<template>
	<div class="d-flex gap-3 flex-column">
		<div class="card rounded-3">
			<div class="card-header">
				<h6 class="my-2">
					<i class="bi bi-magic me-2"></i>
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
		<div class="card rounded-3">
			<div class="card-header">
				<h6 class="my-2">
					<i class="bi bi-ethernet me-2"></i>
					<LocaleText t="Dashboard IP Address & Listen Port"></LocaleText>
				</h6>
			</div>
			<div class="card-body">
				<DashboardIPPortInput></DashboardIPPortInput>
			</div>
		</div>
		
		<!-- Admin Users Management (Multiple Admins) -->
		<DashboardAdminUsers></DashboardAdminUsers>

		<DashboardAPIKeys></DashboardAPIKeys>
		<DashboardEmailSettings></DashboardEmailSettings>
	</div>
</template>

<style scoped>

</style>