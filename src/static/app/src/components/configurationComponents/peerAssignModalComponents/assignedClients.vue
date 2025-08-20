<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {ref} from "vue";
import Assignment from "@/components/configurationComponents/peerAssignModalComponents/assignment.vue";
import {DashboardClientAssignmentStore} from "@/stores/DashboardClientAssignmentStore.js";
const emits = defineEmits(['unassign'])
const props = defineProps(['configurationName', 'peer'])
const assignmentStore = DashboardClientAssignmentStore()
</script>

<template>
	<div class="p-3 bg-body-tertiary rounded-3 d-flex flex-column gap-2">
		<h6 class="mb-0">
			<LocaleText t="Assigned Clients"></LocaleText>
		</h6>
		<TransitionGroup name="list" tag="div" class="position-relative">
			<Assignment :assignment="a" :key="a.AssignmentID"
			            @unassign="assignmentStore.unassignClient(configurationName, peer, a.AssignmentID)"
			            v-for="a in assignmentStore.assignments"></Assignment>
		</TransitionGroup>
		<div class="text-center" v-if="assignmentStore.assignments.length === 0">
			<small class="text-muted">
				<LocaleText t="No client assigned to this peer yet"></LocaleText>
			</small>
		</div>
	</div>
</template>

<style scoped>
.list-move, /* apply transition to moving elements */
.list-enter-active,
.list-leave-active {
	transition: all 0.5s ease;
}

.list-enter-from,
.list-leave-to {
	opacity: 0;
	transform: scale(0.9);
}

/* ensure leaving items are taken out of layout flow so that moving
   animations can be calculated correctly. */
.list-leave-active {
	position: absolute;
	width: 100%;
}

.assignment:last-child{
	margin-bottom: 0 !important;
}
</style>