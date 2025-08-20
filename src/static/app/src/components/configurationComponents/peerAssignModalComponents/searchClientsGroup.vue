<script setup>
import {computed} from "vue";
import LocaleText from "@/components/text/localeText.vue";
import {DashboardClientAssignmentStore} from "@/stores/DashboardClientAssignmentStore.js";

const props = defineProps(['group', 'groupName', 'searchString'])
const emits = defineEmits(['count', 'assign'])
const assignmentStore = DashboardClientAssignmentStore()

const filterGroup = computed(() => {
	let g = props.group.filter(x => 
		!assignmentStore.assignments.map(a => a.Client.ClientID).includes(x.ClientID))
	if (props.searchString){
		let v = g.filter(
			x => (x.Name && x.Name.includes(props.searchString)) || (x.Email && x.Email.includes(props.searchString))
		)
		emits('count', v.length)
		return v
	}
	emits('count', g.length)
	return g
})
</script>

<template>
	<div class="d-flex flex-column gap-2">
		<h6 class="mb-0">
			<small>{{groupName}}</small>
		</h6>
		<div v-if="filterGroup.length > 0" class="d-flex flex-column gap-2">
			<div class="bg-body-secondary rounded-3 text-start p-2 d-flex"
			     v-for="client in filterGroup">
				<div class="d-flex flex-column">
					<small class="mb-0">
						{{ client.Email }}
					</small>
					<small class="text-muted">{{ client.Name ? client.Name : 'No Name' }}</small>
				</div>
				<button
					@click="emits('assign', client.ClientID)"
					:class="{disabled: assignmentStore.assigning}"
					class="btn bg-success-subtle text-success-emphasis ms-auto">
					<span class="spinner-border spinner-border-sm" v-if="assignmentStore.assigning === client.ClientID"></span>
					<i class="bi bi-plus-circle-fill" v-else></i>
				</button>
			</div>
		</div>
		<div v-else>
			<small class="text-muted">
				<LocaleText t="No result"></LocaleText>
			</small>
		</div>
	</div>
</template>

<style scoped>

</style>