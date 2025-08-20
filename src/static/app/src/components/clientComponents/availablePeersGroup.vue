<script setup lang="ts">
import {computed, ref} from "vue";
import {DashboardClientAssignmentStore} from "@/stores/DashboardClientAssignmentStore.js";
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps(['configuration', 'peers', 'clientAssignedPeers', 'availablePeerSearchString'])
const emits = defineEmits(['assign', 'unassign'])
const assignmentStore = DashboardClientAssignmentStore()
const available = computed(() => {
	if (props.clientAssignedPeers){
		if (Object.keys(props.clientAssignedPeers).includes(props.configuration)){
			return props.peers.filter(
				x => {
					return !props.clientAssignedPeers[props.configuration].map(
						x => x.id
					).includes(x.id) &&
						(!props.availablePeerSearchString ||
							(props.availablePeerSearchString &&
								(x.id.includes(props.availablePeerSearchString) || x.name.includes(props.availablePeerSearchString))))
				}
			)
		}
	}
	return props.availablePeerSearchString ? props.peers.filter(
		x => x.id.includes(props.availablePeerSearchString) || x.name.includes(props.availablePeerSearchString)
	) : props.peers
})
const confirmDelete = ref(false)
const collapse = ref(false)
</script>

<template>
	<div class="card rounded-0 border-0">
		<div
			@click="collapse = !collapse"
			role="button"
			class="card-header rounded-0 sticky-top z-5 bg-body-secondary border-0 border-bottom text-white d-flex">
			<small><samp>{{ configuration }}</samp></small>
			<a role="button" class="ms-auto text-white" >
				<i class="bi bi-chevron-compact-down" v-if="collapse"></i>
				<i class="bi bi-chevron-compact-up" v-else></i>
			</a>
		</div>
		<div class="card-body p-0" v-if="!collapse">
			<div class="list-group list-group-flush" >
				<div
					class="list-group-item d-flex border-bottom list-group-item-action d-flex align-items-center gap-3"
					:key="peer.id"
					v-for="peer in available" >
					<div v-if="!confirmDelete">
						<small class="text-body">
							<RouterLink
								class="text-decoration-none"
								target="_blank"
								:to="'/configuration/' + configuration +'/peers?id=' + encodeURIComponent(peer.id)">
								<samp>{{ peer.id }}</samp>
							</RouterLink>
						</small><br>
						<small class="text-muted">
							{{ peer.name ? peer.name : 'Untitled Peer'}}
						</small>
					</div>
					<div v-else>
						<small class="text-body">
							<LocaleText t="Are you sure to remove this peer?"></LocaleText>
						</small><br>
						<small class="text-muted">
							<samp>{{ peer.id }}</samp>
						</small>
					</div>
					<template v-if="clientAssignedPeers">
						<button
							@click="emits('assign', peer.id)"
							:class="{disabled: assignmentStore.assigning}"
							class="btn bg-success-subtle text-success-emphasis ms-auto">
							<i class="bi bi-plus-circle-fill" ></i>
						</button>
					</template>
					<button
						v-else
						@click="emits('unassign', peer.assignment_id)"
						:class="{disabled: assignmentStore.unassigning}"
						aria-label="Delete Assignment"
						class="btn bg-danger-subtle text-danger-emphasis ms-auto">
						<i class="bi bi-trash-fill"></i>
					</button>
				</div>
			</div>

		</div>
	</div>
</template>

<style scoped>

</style>