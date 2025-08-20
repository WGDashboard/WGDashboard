<script setup lang="ts" async>
import {onMounted, ref, watch, watchEffect} from "vue";
import { fetchGet } from "@/utilities/fetch.js"
import {DashboardClientAssignmentStore} from "@/stores/DashboardClientAssignmentStore.js";
import AvailablePeersGroup from "@/components/clientComponents/availablePeersGroup.vue";
import LocaleText from "@/components/text/localeText.vue";
const props = defineProps(['client', 'clientAssignedPeers'])
const loading = ref(false)
const assignmentStore = DashboardClientAssignmentStore()
const manage = ref(false)
const emits = defineEmits(['refresh'])

const assign = async (ConfigurationName, Peer, ClientID) => {
	await assignmentStore.assignClient(ConfigurationName, Peer, ClientID, false)
	emits('refresh')
}

const unassign = async (AssignmentID) => {
	await assignmentStore.unassignClient(undefined, undefined, AssignmentID)
	emits('refresh')
}

const availablePeerSearchString = ref("")

</script>

<template>
<div>
	<div class="d-flex rounded-0 border-0 flex-column d-flex flex-column border-bottom pb-1" v-if="!loading">
		<div class="d-flex flex-column p-3 gap-3">
			<div class="d-flex align-items-center">
				<h6 class="mb-0">
					<LocaleText t="Assigned Peers"></LocaleText>
					<span class="text-bg-primary badge ms-2">
						{{ Object.keys(clientAssignedPeers).length }} <LocaleText :t="Object.keys(clientAssignedPeers).length > 1 ? 'Configurations' : 'Configuration'"></LocaleText>
					</span>
					<span class="text-bg-info badge ms-2">
						{{ Object.values(clientAssignedPeers).flat().length }} <LocaleText :t="Object.values(clientAssignedPeers).flat().length > 1 ? 'Peers' : 'Peer'"></LocaleText>
					</span>
				</h6>
				<button class="btn btn-sm bg-primary-subtle text-primary-emphasis rounded-3 ms-auto"
						@click="manage = !manage">
					<template v-if="!manage">
						<i class="bi bi-list-check me-2"></i>Manage
					</template>
					<template v-else>
						<i class="bi bi-check me-2"></i>Done
					</template>
				</button>
			</div>
			<div class="rounded-3 availablePeers border h-100 overflow-scroll flex-grow-1 d-flex flex-column">
				<AvailablePeersGroup
					:configuration="configuration"
					:peers="peers"
					@unassign="async (id) => await unassign(id)"
					v-for="(peers, configuration) in clientAssignedPeers">
				</AvailablePeersGroup>
				<h6 class="text-muted m-auto p-3" v-if="Object.keys(clientAssignedPeers).length === 0">
					<LocaleText t="No peer assigned to this client"></LocaleText>
				</h6>
			</div>
		</div>
		<div style="height: 500px" class="d-flex flex-column p-3" v-if="manage">
			<div class="availablePeers border h-100 card rounded-3">
				<div class="card-header sticky-top p-3">
					<h6 class="mb-0 d-flex align-items-center">
						<LocaleText t="Available Peers"></LocaleText>
					</h6>
				</div>
				<div class="card-body p-0 overflow-scroll">
					<AvailablePeersGroup
						:availablePeerSearchString="availablePeerSearchString"
						:configuration="configuration"
						:clientAssignedPeers="clientAssignedPeers"
						:peers="peers"
						:key="configuration"
						@assign="async (id) => await assign(configuration, id, props.client.ClientID)"
						v-for="(peers, configuration) in assignmentStore.allConfigurationsPeers">
					</AvailablePeersGroup>
					<h6 class="text-muted m-auto" v-if="Object.keys(assignmentStore.allConfigurationsPeers).length === 0">
						<LocaleText t="No peer is available to assign"></LocaleText>
					</h6>
				</div>
				<div class="card-footer d-flex gap-2 p-3 align-items-center justify-content-end">
					<label for="availablePeerSearchString">
						<i class="bi bi-search me-2"></i>
					</label>
					<input
						id="availablePeerSearchString"
						v-model="availablePeerSearchString"
						class="form-control form-control-sm rounded-3 w-auto" type="text">
				</div>
			</div>
		</div>
	</div>
	<div v-else>
		<div class="p-3 placeholder-glow border-bottom">
			<h6 class="placeholder w-100 rounded-3"></h6>
			<div class="placeholder w-100 rounded-3" style="height: 400px"></div>
		</div>
	</div>
</div>
</template>

<style scoped>

</style>