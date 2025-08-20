<script setup>
import {GetLocale} from "@/utilities/locale.js";
import LocaleText from "@/components/text/localeText.vue";
import {computed, reactive, ref} from "vue";
import SearchClientsGroup from "@/components/configurationComponents/peerAssignModalComponents/searchClientsGroup.vue";
import {fetchPost} from "@/utilities/fetch.js";
import {DashboardClientAssignmentStore} from "@/stores/DashboardClientAssignmentStore.js";

const props = defineProps(['clients', 'newAssignClients', 'assignments'])

const assignmentStore = DashboardClientAssignmentStore()

const selectedGroup = ref("")
const searchString = ref("")
const getSelectedGroup = computed(() => {
	if (selectedGroup.value){
		return {
			[selectedGroup.value] : assignmentStore.clients[selectedGroup.value]
		}
	}
	return assignmentStore.clients
})
const groupCount = reactive({})
Object.keys(assignmentStore.clients).forEach(
	x => groupCount[x] = assignmentStore.clients[x].length
)

const emits = defineEmits(['assign'])
</script>

<template>
	<div class="p-3 bg-body-tertiary rounded-3 position-relative">
		<h6>
			<LocaleText t="Assign to Clients"></LocaleText>
		</h6>
		<label for="SearchClient" class="form-label">
			<small class="text-muted">
				<LocaleText t="Enter Email or Name to Search"></LocaleText>
			</small>
		</label>
		<input class="form-control rounded-3 mb-2"
		       id="SearchClient"
		       v-model="searchString" type="email">
		<div class="w-100 rounded-3 d-flex flex-column gap-2 ">
			<div>
				<small class="text-muted">Groups</small>
				<div class="mt-1">
					<button
						:class="{'active': !selectedGroup}"
						@click="selectedGroup = ''"
						class="btn bg-primary-subtle text-primary-emphasis btn-sm me-2 rounded-3">
						<LocaleText t="All"></LocaleText>
					</button>
					<button 
						@click="selectedGroup = groupName"
						:class="{'active': selectedGroup === groupName}"
						class="btn bg-primary-subtle text-primary-emphasis btn-sm me-2 rounded-3" 
						v-for="(_, groupName) in assignmentStore.clients">
						{{ groupName }} 
							<span class="ms-1 badge" :class="[ groupCount[groupName] > 0 ? 'bg-primary' : 'bg-secondary' ]">
								{{ groupCount[groupName] }}
							</span>
					</button>
				</div>
			</div>
			<div class="p-3 border rounded-3 d-flex flex-column gap-2 overflow-y-scroll" style="height: 400px">
				<SearchClientsGroup
					@assign="(args) => emits('assign', args)"
					@count="(args) => groupCount[groupName] = args"
					:searchString="searchString"
					:group="group" :groupName="groupName" 
					v-for="(group, groupName) in getSelectedGroup"></SearchClientsGroup>
			</div>
		</div>
	</div>
</template>

<style scoped>

</style>