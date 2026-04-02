<script>
import { ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import "animate.css"
import PeerSettingsDropdown from "@/components/configurationComponents/peerSettingsDropdown.vue";
import LocaleText from "@/components/text/localeText.vue";
import {DashboardConfigurationStore} from "@/stores/DashboardConfigurationStore.js";
import {GetLocale} from "@/utilities/locale.js";
import PeerTagBadge from "@/components/configurationComponents/peerTagBadge.vue";

export default {
	name: "peer",
	methods: {GetLocale},
	components: {
		PeerTagBadge, LocaleText, PeerSettingsDropdown
	},
	props: {
		Peer: Object, ConfigurationInfo: Object, order: Number, searchPeersLength: Number
	},
	setup(){
		const target = ref(null);
		const subMenuOpened = ref(false)
		const dashboardStore = DashboardConfigurationStore()
		onClickOutside(target, event => {
			subMenuOpened.value = false;
		});
		return {target, subMenuOpened, dashboardStore}
	},
	computed: {
		getLatestHandshake(){
			if (this.Peer.latest_handshake.includes(",")){
				return this.Peer.latest_handshake.split(",")[0]
			}
			return this.Peer.latest_handshake;
		},
		getDropup(){
			return this.searchPeersLength - this.order <= 3
		}
	}
}
</script>

<template>
	<div class="card shadow-sm rounded-3 peerCard"
		 :id="'peer_'+Peer.id"
		:class="{'border-warning': Peer.restricted}">
		<div>
			<div v-if="!Peer.restricted" class="card-header bg-transparent d-flex align-items-center gap-2 border-0">
				<div class="dot ms-0" :class="{active: Peer.status === 'running'}"></div>
				<div
					style="font-size: 0.8rem; color: #28a745"
					class="d-flex align-items-center"
					v-if="dashboardStore.Configuration.Server.dashboard_peer_list_display === 'list' && Peer.status === 'running'">
					<i class="bi bi-box-arrow-in-right me-2"></i>
					<span>
						{{ Peer.endpoint }}
					</span>
				</div>
				
				
				<div style="font-size: 0.8rem" class="ms-auto d-flex gap-2">
					<span class="text-primary">
						<i class="bi bi-arrow-down"></i><strong>
						{{(Peer.cumu_receive + Peer.total_receive).toFixed(4)}}</strong> GB
					</span>
					<span class="text-success">
						<i class="bi bi-arrow-up"></i><strong>
						{{(Peer.cumu_sent + Peer.total_sent).toFixed(4)}}</strong> GB
					</span>
					<span class="text-secondary" v-if="Peer.latest_handshake !== 'No Handshake'">
						<i class="bi bi-arrows-angle-contract"></i>
						{{getLatestHandshake}} ago
					</span>
				</div>
			</div>
			<div v-else class="border-0 card-header bg-transparent text-warning fw-bold" 
			     style="font-size: 0.8rem">
				<i class="bi-lock-fill me-2"></i>
				<LocaleText t="Access Restricted"></LocaleText>
			</div>
		</div>
		<div class="card-body pt-1" style="font-size: 0.9rem">
			<h6>
				{{Peer.name ? Peer.name : GetLocale('Untitled Peer')}}
			</h6>
			<div class="d-flex"
			     :class="[dashboardStore.Configuration.Server.dashboard_peer_list_display === 'grid' ? 'gap-1 flex-column' : 'flex-row gap-3']">
				<div :class="{'d-flex gap-2 align-items-center' : dashboardStore.Configuration.Server.dashboard_peer_list_display === 'list'}">
					<small class="text-muted">
						<LocaleText t="Public Key"></LocaleText>
					</small>
					<small class="d-block">
						<samp>{{Peer.id}}</samp>
					</small>
				</div>
				<div :class="{'d-flex gap-2 align-items-center' : dashboardStore.Configuration.Server.dashboard_peer_list_display === 'list'}">
					<small class="text-muted">
						<LocaleText t="Allowed IPs"></LocaleText>
					</small>
					<small class="d-block">
						<samp>{{Peer.allowed_ip}}</samp>
					</small>
				</div>
				<div class="d-flex align-items-center gap-1"
					:class="{'ms-auto': dashboardStore.Configuration.Server.dashboard_peer_list_display === 'list'}"
				>
					<PeerTagBadge :BackgroundColor="group.BackgroundColor" :GroupName="group.GroupName" :Icon="'bi-' + group.Icon"
						v-for="group in Object.values(ConfigurationInfo.Info.PeerGroups).filter(x => x.Peers.includes(Peer.id))"
					></PeerTagBadge>
					<div class="ms-auto px-2 rounded-3 subMenuBtn position-relative"
					     :class="{active: this.subMenuOpened}"
					>
						<a role="button" class="text-body"
						   @click="this.subMenuOpened = true">
							<h5 class="mb-0"><i class="bi bi-three-dots"></i></h5>
						</a>
						<Transition name="slide-fade">
							<PeerSettingsDropdown
								:dropup="getDropup"
								@qrcode="this.$emit('qrcode')"
								@configurationFile="this.$emit('configurationFile')"
								@setting="this.$emit('setting')"
								@jobs="this.$emit('jobs')"
								@refresh="this.$emit('refresh')"
								@share="this.$emit('share')"
								@assign="this.$emit('assign')"
								:Peer="Peer"
								:ConfigurationInfo="ConfigurationInfo"
								v-if="this.subMenuOpened"
								ref="target"
							></PeerSettingsDropdown>
						</Transition>
					</div>
				</div>
			</div>
		</div>
		<div class="card-footer" role="button" @click="$emit('details')">
			<small class="d-flex align-items-center">
				<LocaleText t="Details"></LocaleText>
				<i class="bi bi-chevron-right ms-auto"></i>
			</small>
		</div>
	</div>
</template>

<style scoped>



.subMenuBtn.active{
	background-color: #ffffff20;
}

.peerCard{
	transition: box-shadow 0.1s cubic-bezier(0.82, 0.58, 0.17, 0.9);
}

.peerCard:hover{
	box-shadow: var(--bs-box-shadow) !important;
}
</style>