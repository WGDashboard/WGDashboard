<script>
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {fetchGet, fetchPost} from "@/utilities/fetch.js";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js";
import LocaleText from "@/components/text/localeText.vue";
import {GetLocale} from "@/utilities/locale.js";
import PeerTag from "@/components/configurationComponents/peerTag.vue";


export default {
	name: "peerSearch",
	components: {PeerTag, LocaleText},
	setup(){
		const store = DashboardConfigurationStore();
		const wireguardConfigurationStore = WireguardConfigurationsStore()
		return {store, wireguardConfigurationStore}
	},
	props: {
		configuration: Object, displayTags: Array
	},
	data(){
		return {
			sort: {
				status: GetLocale("Status"),
				name: GetLocale("Name"),
				allowed_ip: GetLocale("Allowed IPs"),
				restricted: GetLocale("Restricted")
			},
			interval: {
				'5000': GetLocale('5 Seconds'),
				'10000': GetLocale('10 Seconds'),
				'30000': GetLocale('30 Seconds'),
				'60000': GetLocale('1 Minutes')
			},
			display: {
				grid: GetLocale('Grid'),
				list: GetLocale('List')
			},
			searchString: "",
			searchStringTimeout: undefined,
			showDisplaySettings: false,
			showMoreSettings: false,
			tagManager: false
		}
	},
	methods: {
		updateSort(sort){
			fetchPost("/api/updateDashboardConfigurationItem", {
				section: "Server",
				key: "dashboard_sort",
				value: sort
			}, (res) => {
				if (res.status){
					this.store.getConfiguration();
				}
			})
		},
		updateRefreshInterval(refreshInterval){
			fetchPost("/api/updateDashboardConfigurationItem", {
				section: "Server",
				key: "dashboard_refresh_interval",
				value: refreshInterval
			}, (res) => {
				if (res.status){
					this.store.getConfiguration();
				}
			})
		},
		updateDisplay(display){
			fetchPost("/api/updateDashboardConfigurationItem", {
				section: "Server",
				key: "dashboard_peer_list_display",
				value: display
			}, (res) => {
				if (res.status){
					this.store.getConfiguration();
				}
			})	
		},
		downloadAllPeer(){
			fetchGet(`/api/downloadAllPeers/${this.configuration.Name}`, {}, (res) => {
				res.data.forEach(x => {
					x.fileName = x.fileName + '.conf'
				})
				window.wireguard.generateZipFiles(res, this.configuration.Name)
			})
		}
	}
}
</script>

<template>
	<div class="d-flex flex-column gap-2 my-4">
		<div class="d-flex gap-2 peerSearchContainer">
			<div class="dropdown">
				<button
					data-bs-toggle="dropdown"
					class="btn w-100 btn-sm text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle  position-relative">
					<i class="bi bi-sort-up me-2"></i>
					<LocaleText t="Sort By"></LocaleText>
					<span class="badge text-bg-primary ms-2">{{this.sort[store.Configuration.Server.dashboard_sort]}}</span>
				</button>
				<ul class="dropdown-menu rounded-3">
					<li v-for="(value, key) in this.sort" >
						<button class="dropdown-item d-flex align-items-center" @click="this.updateSort(key)">
							<small>
								{{ value }}
							</small>
							<small class="ms-auto">
								<i class="bi bi-check-circle-fill"
								   v-if="store.Configuration.Server.dashboard_sort === key"></i>
							</small>
						</button>
					</li>
				</ul>
			</div>
			<div class="dropdown">
				<button
					data-bs-toggle="dropdown"
					class="btn btn-sm w-100 text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle  position-relative">
					<i class="bi bi-arrow-repeat me-2"></i>
					<LocaleText t="Refresh Interval"></LocaleText>
					<span class="badge text-bg-primary ms-2">{{this.interval[store.Configuration.Server.dashboard_refresh_interval]}}</span>
				</button>
				<ul class="dropdown-menu rounded-3">
					<li v-for="(value, key) in this.interval" >
						<button class="dropdown-item d-flex align-items-center" @click="this.updateRefreshInterval(key)">
							<small>
								{{ value }}
							</small>
							<small class="ms-auto">
								<i class="bi bi-check-circle-fill"
								   v-if="store.Configuration.Server.dashboard_refresh_interval === key"></i>
							</small>
						</button>
					</li>
				</ul>
			</div>
			<div class="dropdown">
				<button
					data-bs-toggle="dropdown"
					class="btn btn-sm w-100 text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle  position-relative">
					<i class="bi me-2" :class="'bi-' + store.Configuration.Server.dashboard_peer_list_display"></i>
					<LocaleText t="Display"></LocaleText>
					<span class="badge text-bg-primary ms-2">{{this.display[store.Configuration.Server.dashboard_peer_list_display]}}</span>
				</button>
				<ul class="dropdown-menu rounded-3">
					<li v-for="(value, key) in this.display" >
						<button class="dropdown-item d-flex align-items-center" @click="this.updateDisplay(key)">
							<small>
								{{ value }}
							</small>
							<small class="ms-auto">
								<i class="bi bi-check-circle-fill"
								   v-if="store.Configuration.Server.dashboard_peer_list_display === key"></i>
							</small>
						</button>
					</li>
				</ul>
			</div>
			<div class="position-relative">
				<button
					@click="tagManager = !tagManager"
					class="btn btn-sm w-100 text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle  position-relative">

					<i class="bi me-2 bi-tag"></i>
					<LocaleText t="Tags"></LocaleText>

				</button>
				<Transition name="slide-fade">
					<PeerTag
						@update="args => configuration.Info.PeerGroups = args"
						@close="this.tagManager = false"
						:configuration="configuration" v-if="this.tagManager"></PeerTag>
				</Transition>
			</div>
			
			<button class="btn btn-sm text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle ms-lg-auto"
			        @click="this.$emit('search')">
				<i class="bi bi-search me-2"></i>
				<LocaleText t="Search"></LocaleText>
			</button>
			<button class="btn btn-sm text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle"
			        @click="this.downloadAllPeer()">
				<i class="bi bi-download me-2 me-lg-0 me-xl-2"></i>
				<LocaleText t="Download All" class="d-sm-block d-lg-none d-xl-block"></LocaleText>
			</button>
			<button class="btn btn-sm text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle "
			        @click="this.$emit('selectPeers')">
				<i class="bi bi-check2-all me-2 me-lg-0 me-xl-2"></i>
				<LocaleText t="Select Peers" class="d-sm-block d-lg-none d-xl-block"></LocaleText>
			</button>
			<button class="btn btn-sm text-primary-emphasis bg-primary-subtle rounded-3 border-1 border-primary-subtle "
			        @click="this.$emit('jobsAll')"
			        type="button" aria-expanded="false">
				<i class="bi bi-person-walking me-2 me-lg-0 me-xl-2"></i>
				<LocaleText t="Active Jobs" class="d-sm-block d-lg-none d-xl-block"></LocaleText>
			</button>
		</div>
	</div>
</template>

<style scoped>

.animation__fadeInDropdown{
	animation-name: fadeInDropdown;
	animation-duration: 0.2s;
	animation-timing-function: cubic-bezier(0.82, 0.58, 0.17, 0.9);
}

@keyframes fadeInDropdown{
	0%{
		opacity: 0;
		filter: blur(3px);
		transform: translateY(-60px);
	}
	100%{
		opacity: 1;
		filter: blur(0px);
		transform: translateY(-40px);
	}
}

.displayModal .dashboardModal{
	width: 400px !important;
}

@media screen and (max-width: 992px) {
	.peerSearchContainer{
		flex-direction: column;
	}
	
	.peerSettingContainer .dashboardModal{
		width: 100% !important;
	}
}


.peerSearchContainer > button, .peerSearchContainer .dropdown > button{
	text-align: left;
	display: flex;
	align-items: center;
	
}
</style>