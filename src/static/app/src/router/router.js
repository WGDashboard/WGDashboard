import { createRouter, createWebHashHistory } from 'vue-router'
import {cookie} from "../utilities/cookie.js";
import {fetchGet} from "@/utilities/fetch.js";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";

const checkAuth = async () => {
	let result = false
	await fetchGet("/api/validateAuthentication", {}, (res) => {
		result = res.status
	});
	return result;
}

const router = createRouter({
	history: createWebHashHistory(),
	scrollBehavior(){
		if (document.querySelector("main") !== null){
			document.querySelector("main").scrollTo({
				top: 0
			})
		}
	},
	routes: [
		{
			name: "Index",
			path: '/',
			component: () => import('@/views/index.vue'),
			meta: {
				requiresAuth: true,
			},
			children: [
				{
					name: "Configuration List",
					path: '',
					component: () => import('@/components/configurationList.vue'),
					meta: {
						title: "WireGuard Configurations"
					}
				},
				{
					name: "Settings",
					path: 'settings',
					component: () => import('@/views/settings.vue'),
					meta: {
						title: "Settings"
					}
				},
				{
					path: 'ping',
					name: "Ping",
					component: () => import('@/views/ping.vue'),
				},
				{
					path: 'traceroute',
					name: "Traceroute",
					component: () => import('@/views/traceroute.vue'),
				},
				{
					name: "New Configuration",
					path: 'new_configuration',
					component: () => import('@/views/newConfiguration.vue'),
					meta: {
						title: "New Configuration"
					}
				},
				{
					name: "Restore Configuration",
					path: 'restore_configuration',
					component: () => import('@/views/restoreConfiguration.vue'),
					meta: {
						title: "Restore Configuration"
					}
				},
				{
					name: "System Status",
					path: 'system_status',
					component: () => import("@/views/systemStatus.vue"),
					meta: {
						title: "System Status"
					}
				},
				{
					name: "Clients",
					path: 'clients',
					component: () => import("@/views/clients.vue"),
					meta: {
						title: "Clients"
					},
					children: [
						{
							name: "Client Viewer",
							path: ':id',
							component: () => import('@/components/clientComponents/clientViewer.vue'),
							meta: {
								title: "Clients"
							},
						}
					]
				},
				{
					name: "Configuration",
					path: 'configuration/:id',
					component: () => import('@/views/configuration.vue'),
					meta: {
						title: "Configuration"
					},
					children: [
						{
							name: "Peers List",
							path: 'peers',
							component: () => import('@/components/configurationComponents/peerList.vue')
						}
					]
				},

			]
		},
		{
			path: '/signin', 
			component: () => import('@/views/signin.vue'),
			meta: {
				title: "Sign In",
				hideTopNav: true
			}
		},
		{
			path: '/welcome', 
			component: () => import("@/views/setup.vue"),
			meta: {
				requiresAuth: true,
				title: "Welcome to WGDashboard",
				hideTopNav: true
			},
		},
		{
			path: '/2FASetup', 
			component: () => import("@/components/setupComponent/totp.vue"),
			meta: {
				requiresAuth: true,
				title: "Multi-Factor Authentication Setup",
				hideTopNav: true
			},
		},
		{
			path: '/share', 
			component: () => import("@/views/share.vue"),
			meta: {
				title: "Share",
				hideTopNav: true
			}
		}
	]
});

router.beforeEach(async (to, from, next) => {
	const wireguardConfigurationsStore = WireguardConfigurationsStore();
	const dashboardConfigurationStore = DashboardConfigurationStore();

	if (to.meta.title){
		document.title = to.meta.title + " | WGDashboard";
	}else if(to.params.id){
		document.title = to.params.id + " | WGDashboard";
	}else{
		document.title = "WGDashboard"
	}
	dashboardConfigurationStore.ShowNavBar = false;
	document.querySelector(".loadingBar").classList.remove("loadingDone")
	document.querySelector(".loadingBar").classList.add("loading")
	if (to.meta.requiresAuth){
		if (!dashboardConfigurationStore.getActiveCrossServer()){
			if (await checkAuth()){
				await dashboardConfigurationStore.getConfiguration()
				if (!wireguardConfigurationsStore.Configurations && to.name !== "Configuration List"){
					await wireguardConfigurationsStore.getConfigurations();
				}
				dashboardConfigurationStore.Redirect = undefined;
				next()
			}else{
				dashboardConfigurationStore.Redirect = to;
				next("/signin")
				dashboardConfigurationStore.newMessage("WGDashboard", "Sign in session ended, please sign in again", "warning")
			}
		}else{
			await dashboardConfigurationStore.getConfiguration()
			if (!wireguardConfigurationsStore.Configurations && to.name !== "Configuration List"){
				await wireguardConfigurationsStore.getConfigurations();
			}
			next()
		}
	}else {
		next()
	}
});

router.afterEach(() => {
	document.querySelector(".loadingBar").classList.remove("loading")
	document.querySelector(".loadingBar").classList.add("loadingDone")
})
export default router