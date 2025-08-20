<script>
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchGet} from "@/utilities/fetch.js";
import LocaleText from "@/components/text/localeText.vue";
import {GetLocale} from "@/utilities/locale.js";
import HelpModal from "@/components/navbarComponents/helpModal.vue";
import AgentModal from "@/components/navbarComponents/agentModal.vue";

export default {
	name: "navbar",
	components: {HelpModal, LocaleText, AgentModal},
	setup(){
		const wireguardConfigurationsStore = WireguardConfigurationsStore();
		const dashboardConfigurationStore = DashboardConfigurationStore();
		return {wireguardConfigurationsStore, dashboardConfigurationStore}
	},
	data(){
		return {
			updateAvailable: false,
			updateMessage: "Checking for update...",
			updateUrl: "",
			openHelpModal: false,
			openAgentModal: false,
		}
	},
	computed: {
		getActiveCrossServer(){
			if (this.dashboardConfigurationStore.ActiveServerConfiguration){
				return new URL(this.dashboardConfigurationStore.CrossServerConfiguration.ServerList
					[this.dashboardConfigurationStore.ActiveServerConfiguration].host)
			}
			return undefined
		}
	},
	async mounted() {
		await this.wireguardConfigurationsStore.getConfigurations();
		await fetchGet("/api/getDashboardUpdate", {}, (res) => {
			if (res.status){
				if (res.data){
					this.updateAvailable = true
					this.updateUrl = res.data
				}
				this.updateMessage = res.message
			}else{
				this.updateMessage = GetLocale("Failed to check available update")
				console.log(`Failed to get update: ${res.message}`)
			}
		})
		this.wireguardConfigurationsStore.ConfigurationListInterval = setInterval(() => {
			this.wireguardConfigurationsStore.getConfigurations()
		}, 10000)
	}
}
</script>

<template>
	<div class="col-md-3 col-lg-2 d-md-block p-2 navbar-container bg-transparent"
	     :class="{active: this.dashboardConfigurationStore.ShowNavBar}"
	     :data-bs-theme="dashboardConfigurationStore.Configuration.Server.dashboard_theme"
	>
		<nav id="sidebarMenu" class=" bg-body-tertiary sidebar border h-100 rounded-3 shadow overflow-y-scroll" >
			<div class="sidebar-sticky ">
				<div class="text-white text-center m-0 py-3 mb-2 btn-brand">
					<h5 class="mb-0">
						WGDashboard
					</h5>
					<small class="ms-auto" v-if="getActiveCrossServer !== undefined">
						<i class="bi bi-hdd-rack-fill me-2"></i>{{getActiveCrossServer.host}}
					</small>
				</div>
				<ul class="nav flex-column px-2 gap-1">
					<li class="nav-item">
						<RouterLink class="nav-link rounded-3"
						            to="/" exact-active-class="active">
							<i class="bi bi-house me-2"></i>
							<LocaleText t="Home"></LocaleText>	
						</RouterLink></li>
					<li class="nav-item">
						<RouterLink class="nav-link rounded-3" to="/settings" 
						            active-class="active">
							<i class="bi bi-gear me-2"></i>
							<LocaleText t="Settings"></LocaleText>	
						</RouterLink>
					</li>
					<li class="nav-item">
						<RouterLink class="nav-link rounded-3" to="/clients"
						            active-class="active">
							<i class="bi bi-people me-2"></i>
							<LocaleText t="Clients"></LocaleText>
						</RouterLink>
					</li>
					<li class="nav-item">
						<a class="nav-link rounded-3" role="button" @click="openAgentModal = true">
							<i class="bi bi-question-circle me-2"></i>
							<LocaleText t="Help"></LocaleText>
						</a>
					</li>
				</ul>
				<hr class="text-body my-2">
				<h6 class="sidebar-heading px-3 mt-3 mb-1 text-muted text-center">
					<LocaleText t="WireGuard Configurations"></LocaleText>
				</h6>
				<ul class="nav flex-column px-2 gap-1">
					<li class="nav-item" v-for="c in this.wireguardConfigurationsStore.sortConfigurations">
						<RouterLink :to="'/configuration/'+c.Name + '/peers'" class="nav-link nav-conf-link rounded-3"
						            active-class="active"
						            >
							<span class="dot me-2" :class="{active: c.Status}"></span>
							{{c.Name}}
						</RouterLink>
					</li>
				</ul>
				<hr class="text-body my-2">
				<h6 class="sidebar-heading px-3 mt-3 mb-1 text-muted text-center">
					<LocaleText t="Tools"></LocaleText>
				</h6>
				<ul class="nav flex-column px-2 gap-1">
					<li class="nav-item">
						<RouterLink to="/system_status" class="nav-link rounded-3" active-class="active">
							<LocaleText t="System Status"></LocaleText>
						</RouterLink>
					</li>
					<li class="nav-item">
						<RouterLink to="/ping" class="nav-link rounded-3" active-class="active">
							<LocaleText t="Ping"></LocaleText>
						</RouterLink></li>
					<li class="nav-item">
						<RouterLink to="/traceroute" class="nav-link rounded-3" active-class="active">
							<LocaleText t="Traceroute"></LocaleText>
						</RouterLink>
					</li>
				</ul>
				<hr class="text-body my-2">
				<ul class="nav flex-column px-2 mb-3">
					<li class="nav-item">
						<a class="nav-link text-danger rounded-3" 
					                        @click="this.dashboardConfigurationStore.signOut()" 
					                        role="button" style="font-weight: bold">
							<i class="bi bi-box-arrow-left me-2"></i>
							<LocaleText t="Sign Out"></LocaleText>	
						</a>
					</li>
					<li class="nav-item" style="font-size: 0.8rem">
						<a :href="this.updateUrl" v-if="this.updateAvailable" class="text-decoration-none rounded-3" target="_blank">
							<small class="nav-link text-muted rounded-3" >
								<LocaleText :t="this.updateMessage"></LocaleText>
								(<LocaleText t="Current Version:"></LocaleText> {{ dashboardConfigurationStore.Configuration.Server.version }})
							</small>
						</a>
						<small class="nav-link text-muted rounded-3" v-else>
							<LocaleText :t="this.updateMessage"></LocaleText>
							({{ dashboardConfigurationStore.Configuration.Server.version }})
						</small>
					</li>
				</ul>
			</div>
		</nav>
		<Transition name="zoom">
			<HelpModal v-if="this.openHelpModal" @close="openHelpModal = false;"></HelpModal>
		</Transition>
		<Transition name="slideIn">
			<AgentModal v-if="this.openAgentModal" @close="openAgentModal = false"></AgentModal>
		</Transition>
	</div>
</template>

<style scoped>
@media screen and (max-width: 768px) {
	.navbar-container{
		position: absolute !important;
		z-index: 1000;
		animation-duration: 0.4s;
		animation-fill-mode: both;
		display: none;
		animation-timing-function: cubic-bezier(0.82, 0.58, 0.17, 0.9);
	}
	
	.navbar-container.active{
		animation-direction: normal;
		display: block !important;
		animation-name: zoomInFade
	}
}

.navbar-container{
	height: 100vh;
	position: relative;
}


@supports (height: 100dvh) {
	@media screen and (max-width: 768px){
		.navbar-container{
			height: calc(100dvh - 58px);
		}	
	}
	

}


@keyframes zoomInFade {
	0%{
		opacity: 0;
		transform: translateY(60px);
		filter: blur(3px);
	}
	100%{
		opacity: 1;
		transform: translateY(0px);
		filter: blur(0px);
	}
}

.slideIn-enter-active,
.slideIn-leave-active{
	transition: all 0.3s cubic-bezier(0.82, 0.58, 0.17, 1);
}

.slideIn-enter-from,
.slideIn-leave-to {
	transform: translateY(30px);
	filter: blur(3px);
	opacity: 0;
}
</style>