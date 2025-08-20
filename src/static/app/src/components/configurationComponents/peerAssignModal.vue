<script setup async>
import LocaleText from "@/components/text/localeText.vue";
import SearchClients from "@/components/configurationComponents/peerAssignModalComponents/searchClients.vue";
import AssignedClients from "@/components/configurationComponents/peerAssignModalComponents/assignedClients.vue";
import {DashboardClientAssignmentStore} from "@/stores/DashboardClientAssignmentStore.js";

const props = defineProps({
	selectedPeer: Object
})
const emits = defineEmits([
	'close'
])
const assignmentStore = DashboardClientAssignmentStore()

if (assignmentStore.clients.length > 0){
	assignmentStore.getClients()
}else{
	await assignmentStore.getClients()
}

await assignmentStore.getAssignedClients(props.selectedPeer.configuration.Name, props.selectedPeer.id)
const assignClient = async (clientID) => {
	await assignmentStore.assignClient(props.selectedPeer.configuration.Name, props.selectedPeer.id, clientID)
}
</script>

<template>
	<div class="peerSettingContainer w-100 h-100 position-absolute top-0 start-0 overflow-y-scroll">
		<div class="container d-flex h-100 w-100">
			<div class="m-auto modal-dialog-centered dashboardModal" style="width: 700px">
				<div class="card rounded-3 shadow flex-grow-1">
					<div class="card-header bg-transparent d-flex align-items-center gap-2 border-0 p-4">
						<h4 class="mb-0">
							<LocaleText t="Assign Peer to Client"></LocaleText>
						</h4>
						<button type="button" class="btn-close ms-auto" @click="emits('close')"></button>
					</div>
					<div class="card-body px-4 pb-4 d-flex gap-2 flex-column">
						<AssignedClients
							:configuration-name="props.selectedPeer.configuration.Name"
							:peer="props.selectedPeer.id"
						></AssignedClients>
						<SearchClients
							@assign="args => assignClient(args)"></SearchClients>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style scoped>
*:focus {
	outline: none;
}
</style>