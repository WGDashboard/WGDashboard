<script setup lang="ts">
import LocaleText from "@/components/text/localeText.vue";
import { fetchPost } from "@/utilities/fetch"
import {ref} from "vue";
import { DashboardConfigurationStore } from "@/stores/DashboardConfigurationStore.js"

const props = defineProps(['client'])
const deleting = ref(false)
const confirmDelete = ref(false)
const emits = defineEmits(['refresh'])
const dashboardConfigurationStore = DashboardConfigurationStore()
const deleteClient = async () => {
	deleting.value = true
	await fetchPost("/api/clients/deleteClient", {
		ClientID: props.client.ClientID
	}, (res) => {
		deleting.value = false
		if (res.status){
			emits("deleteSuccess")
			dashboardConfigurationStore.newMessage("Server", "Delete client successfully", "success")
		}else {
			dashboardConfigurationStore.newMessage("Server", "Failed to delete client", "danger")
		}
	})
}
</script>

<template>
	<div class="p-3 d-flex gap-3 flex-column border-bottom">
		<div class="d-flex align-items-center gap-2">
			<h6 class="mb-0">
				<LocaleText t="Delete Client" v-if="!confirmDelete"></LocaleText>
				<LocaleText t="Are you sure to delete this client?" v-else></LocaleText>
			</h6>
			<button class="btn btn-sm bg-danger-subtle text-danger-emphasis rounded-3 ms-auto"
					v-if="!confirmDelete"
					@click="confirmDelete = true"
			>
				<i class="bi bi-trash-fill me-2"></i>
				<LocaleText t="Delete"></LocaleText>
			</button>

			<template v-if="confirmDelete">
				<button
					@click="deleteClient"
					class="btn btn-sm bg-danger-subtle text-danger-emphasis rounded-3 ms-auto">
					<i class="bi bi-trash-fill me-2"></i>
					<LocaleText t="Yes"></LocaleText>
				</button>
				<button class="btn btn-sm bg-secondary-subtle text-secondary-emphasis rounded-3"
						v-if="confirmDelete" @click="confirmDelete = false">
					<i class="bi bi-x-lg me-2"></i>
					<LocaleText t="No"></LocaleText>
				</button>
			</template>
		</div>
	</div>
</template>

<style scoped>

</style>