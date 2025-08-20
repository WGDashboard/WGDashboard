<script setup lang="ts">
import {ref} from "vue";
import { fetchPost } from "@/utilities/fetch.js"

const props = defineProps(['configuration'])
const description = ref(props.configuration.Info.Description)
const showStatus = ref(false)
const status = ref(false)

const updateDescription = async () => {
	await fetchPost("/api/updateWireguardConfigurationInfo", {
		Name: props.configuration.Name,
		Key: "Description",
		Value: description.value
	}, (res) => {
		status.value = res.status
		toggleStatus()
	})
}

const toggleSuccess = () => {
	status.value = true
	toggleStatus()
}

const toggleFail = () => {
	status.value = false
	toggleStatus()
}

const toggleStatus = () => {
	showStatus.value = true
	setTimeout(() => {
		showStatus.value = false
	}, 3000)
}
</script>

<template>
	<div class="d-flex gap-1 flex-column">
		<label for="configurationDescription">
			<small style="white-space: nowrap" class="text-muted">
				<i class="bi bi-pencil-fill me-2"></i>Notes
			</small>
		</label>
		<input type="text"
			   :class="[showStatus ? [status ? 'is-valid':'is-invalid'] : undefined]"
			   id="configurationDescription"
			   v-model="description"
			   @change="updateDescription()"
			   class="form-control rounded-3 bg-transparent form-control-sm">
	</div>
</template>

<style scoped>

</style>