<script setup lang="ts">
import LocaleText from "@/components/text/localeText.vue";
import {ref} from "vue";

import {
	Chart,
	LineElement,
	BarElement,
	BarController,
	LineController,
	LinearScale,
	Legend,
	Title,
	Tooltip,
	CategoryScale,
	PointElement,
	Filler
} from 'chart.js';
Chart.register(
	LineElement,
	BarElement,
	BarController,
	LineController,
	LinearScale,
	Legend,
	Title,
	Tooltip,
	CategoryScale,
	PointElement,
	Filler
);
import PeerSessions from "@/components/peerDetailsModalComponents/peerSessions.vue";
import PeerTraffics from "@/components/peerDetailsModalComponents/peerTraffics.vue";
import PeerEndpoints from "@/components/peerDetailsModalComponents/peerEndpoints.vue";
const props = defineProps(['selectedPeer'])
const selectedDate = ref(undefined)
defineEmits(['close'])
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll ">
		<div class="d-flex h-100 w-100 pb-2">
			<div class="m-auto w-100 p-2">
				<div class="card rounded-3 shadow h-100" >
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4 pb-2">
						<h4 class="mb-0 fw-normal">
							<LocaleText t="Peer Details"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="$emit('close')"></button>
					</div>
					<div class="card-body px-4">
						<div>
							<p class="mb-0 text-muted"><small>
								<LocaleText t="Peer"></LocaleText>
							</small></p>
							<h2>
								{{ selectedPeer.name }}
							</h2>
						</div>
						<div class="row mt-3 gy-2 gx-2 mb-2">
							<div class="col-12 col-lg-3">
								<div class="card rounded-3 bg-transparent h-100">
									<div class="card-body py-2 d-flex flex-column justify-content-center">
										<p class="mb-0 text-muted"><small>
											<LocaleText t="Status"></LocaleText>
										</small></p>
										<div class="d-flex align-items-center">
											<span class="dot ms-0 me-2" :class="{active: selectedPeer.status === 'running'}"></span>
											<LocaleText t="Connected" v-if="selectedPeer.status === 'running'"></LocaleText>
											<LocaleText t="Disconnected" v-else></LocaleText>
										</div>
									</div>
								</div>
							</div>
							<div class="col-12 col-lg-3">
								<div class="card rounded-3 bg-transparent  h-100">
									<div class="card-body py-2 d-flex flex-column justify-content-center">
										<p class="mb-0 text-muted"><small>
											<LocaleText t="Allowed IPs"></LocaleText>
										</small></p>
										{{selectedPeer.allowed_ip}}
									</div>
								</div>
							</div>
							<div style="word-break: break-all" class="col-12 col-lg-6">
								<div class="card rounded-3 bg-transparent h-100">
									<div class="card-body py-2 d-flex flex-column justify-content-center">
										<p class="mb-0 text-muted"><small>
											<LocaleText t="Public Key"></LocaleText>
										</small></p>
										<samp>{{selectedPeer.id}}</samp>
									</div>
								</div>
							</div>

							<div class="col-12 col-lg-3">
								<div class="card rounded-3 bg-transparent  h-100">
									<div class="card-body d-flex">
										<div>
											<p class="mb-0 text-muted"><small>
												<LocaleText t="Latest Handshake Time"></LocaleText>
											</small></p>
											<strong class="h4">
												<LocaleText :t="selectedPeer.latest_handshake !== 'No Handshake' ? selectedPeer.latest_handshake + ' ago': 'No Handshake'"></LocaleText>
											</strong>
										</div>
										<i class="bi bi-person-raised-hand ms-auto h2 text-muted"></i>
									</div>
								</div>
							</div>
							<div class="col-12 col-lg-3">
								<div class="card rounded-3 bg-transparent  h-100">
									<div class="card-body d-flex">
										<div>
											<p class="mb-0 text-muted"><small>
												<LocaleText t="Total Usage"></LocaleText>
											</small></p>
											<strong class="h4 text-warning">
												{{ (selectedPeer.total_data + selectedPeer.cumu_data).toFixed(4) }} GB
											</strong>
										</div>
										<i class="bi bi-arrow-down-up ms-auto h2 text-muted"></i>
									</div>
								</div>
							</div>
							<div class="col-12 col-lg-3">
								<div class="card rounded-3 bg-transparent  h-100">
									<div class="card-body d-flex">
										<div>
											<p class="mb-0 text-muted"><small>
												<LocaleText t="Total Received"></LocaleText>
											</small></p>
											<strong class="h4 text-primary">{{(selectedPeer.total_receive + selectedPeer.cumu_receive).toFixed(4)}} GB</strong>
										</div>
										<i class="bi bi-arrow-down ms-auto h2 text-muted"></i>
									</div>
								</div>
							</div>
							<div class="col-12 col-lg-3">
								<div class="card rounded-3 bg-transparent  h-100">
									<div class="card-body d-flex">
										<div>
											<p class="mb-0 text-muted"><small>
												<LocaleText t="Total Sent"></LocaleText>
											</small></p>
											<strong class="h4 text-success">{{(selectedPeer.total_sent + selectedPeer.cumu_sent).toFixed(4)}} GB</strong>
										</div>
										<i class="bi bi-arrow-up ms-auto h2 text-muted"></i>
									</div>
								</div>
							</div>
							<div class="col-12">
								<PeerTraffics
									:selectedDate="selectedDate"
									:selectedPeer="selectedPeer"></PeerTraffics>
							</div>
							<div class="col-12">
								<PeerSessions
									:selectedDate="selectedDate"
									@selectDate="args => selectedDate = args"
									:selectedPeer="selectedPeer"></PeerSessions>
							</div>
							<div class="col-12">
								<PeerEndpoints
									:selectedPeer="selectedPeer"
								>
								</PeerEndpoints>
							</div>
						</div>


					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>