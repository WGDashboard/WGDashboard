<script setup>
import {ref} from "vue";
import LocaleText from "@/components/text/localeText.vue";
import {DashboardClientAssignmentStore} from "@/stores/DashboardClientAssignmentStore.js";
const props = defineProps(['assignment'])
const emits = defineEmits(['unassign'])
const confirmDelete = ref(false)
const assignmentStore = DashboardClientAssignmentStore()


</script>

<template>
	<div class="bg-body-secondary rounded-3 text-start p-2 mb-2 assignment">
		<div class="d-flex" v-if="!confirmDelete">
			<div class="d-flex flex-column">
				<small>
					{{ assignment.Client.Email }}
				</small>
				<small class="text-muted">
					{{ assignment.Client.Name ? assignment.Client.Name + ' | ' : '' }}{{ assignment.Client.ClientGroup ? assignment.Client.ClientGroup : 'Local' }}
				</small>
			</div>
			<button
				v-if="!confirmDelete"
				@click="confirmDelete = !confirmDelete"
				:class="{disabled: assignmentStore.unassigning}"
				aria-label="Delete Assignment"
				class="btn bg-danger-subtle text-danger-emphasis ms-auto">
				<i class="bi bi-trash-fill"></i>
			</button>
		</div>
		<div class="d-flex gap-2" v-else>
			<div class="d-flex flex-column">
				<small>
					<LocaleText t="Are you sure to delete assignment for"></LocaleText>
				</small>
				<small class="text-muted">
					<LocaleText :t="assignment.Client.Email + ' in group ' + (assignment.Client.ClientGroup ? assignment.Client.ClientGroup : 'Local') + '?'"></LocaleText>
				</small>
			</div>
			<button
				@click="emits('unassign')"
				aria-label="Delete Assignment"
				:class="{disabled: assignmentStore.unassigning}"
				class="btn bg-danger-subtle text-danger-emphasis ms-auto">
				<span class="spinner-border spinner-border-sm" v-if="assignmentStore.unassigning"></span>
				<i class="bi bi-check-lg" v-else></i>
			</button>
			<button
				:class="{disabled: assignmentStore.unassigning}"
				@click="confirmDelete = !confirmDelete"
				aria-label="Cancel Delete Assignment"
				class="btn bg-secondary-subtle text-secondary-emphasis ">
				<i class="bi bi-x-lg"></i>
			</button>
			
		</div>
	</div>
</template>

<style scoped>

</style>