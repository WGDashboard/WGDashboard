<script>
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchPost} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";

export default {
	name: "dashboardTheme",
	components: {LocaleText},
	setup(){
		const dashboardConfigurationStore = DashboardConfigurationStore();
		return {dashboardConfigurationStore}
	},
	methods: {
		async switchTheme(value){
			await fetchPost("/api/updateDashboardConfigurationItem", {
				section: "Server",
				key: "dashboard_theme",
				value: value
			}, (res) => {
				if (res.status){
					this.dashboardConfigurationStore.Configuration.Server.dashboard_theme = value;
				}
			});
		}
	}
}
</script>

<template>
	<div >
		<small class="text-muted mb-1 d-block">
			<strong>
				<LocaleText t="Theme"></LocaleText>
			</strong>
		</small>
		<div class="d-flex gap-1">
			<button class="btn bg-primary-subtle text-primary-emphasis flex-grow-1"
			        @click="this.switchTheme('system')"
			        :class="{active: this.dashboardConfigurationStore.Configuration.Server.dashboard_theme === 'system'}">
				<i class="bi bi-circle-half me-2"></i>
				<LocaleText t="System"></LocaleText>
			</button>
			<button class="btn bg-primary-subtle text-primary-emphasis flex-grow-1"
			        @click="this.switchTheme('light')"
			        :class="{active: this.dashboardConfigurationStore.Configuration.Server.dashboard_theme === 'light'}">
				<i class="bi bi-sun-fill me-2"></i>
				<LocaleText t="Light"></LocaleText>
			</button>
			<button class="btn bg-primary-subtle text-primary-emphasis flex-grow-1"
			        @click="this.switchTheme('dark')"
			        :class="{active: this.dashboardConfigurationStore.Configuration.Server.dashboard_theme === 'dark'}">
				<i class="bi bi-moon-fill me-2"></i>
				<LocaleText t="Dark"></LocaleText>
			</button>
		</div>
	</div>
</template>

<style scoped>

</style>
