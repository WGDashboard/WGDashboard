<script setup lang="ts">
import LocaleText from "@/components/text/localeText.vue";
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js"
import {ref} from "vue";
const store = WireguardConfigurationsStore();
const props = defineProps(['group', 'edit', 'groupId'])
const emits = defineEmits(['delete', 'iconPickerOpen', 'colorPickerOpen', 'toggle'])
const groupName = ref(props.group.GroupName)
const toggleTag = () => {
	if (store.Filter.HiddenTags.includes(props.groupId)){
		store.Filter.HiddenTags = store.Filter.HiddenTags.filter(x => x !== props.groupId)
	}else{
		store.Filter.HiddenTags.push(props.groupId)
	}
}

</script>

<template>
<div class="border rounded-3 p-2">
	<div
		class=" align-items-center overflow-scroll d-flex gap-2 position-relative">
		<button
			@click="emits('iconPickerOpen')"
			aria-label="Pick icon button"
			:class="{disabled: !edit}"
			class="d-flex align-items-center p-2 btn btn-sm border rounded-2">
			<i class="bi" :class="'bi-' + group.Icon" :aria-label="group.Icon" v-if="group.Icon"></i>
			<span style="white-space: nowrap" v-else>
					<LocaleText t="No Icon"></LocaleText>
			</span>
		</button>
		<button
			:class="{disabled: !edit}"
			aria-label="Pick color button"
			@click="emits('colorPickerOpen')"
			:style="{'background-color': group.BackgroundColor, 'color': store.colorText(group.BackgroundColor)}"
			class="d-flex align-items-center  p-2 btn btn-sm border rounded-2">
			<i class="bi bi-eyedropper" ></i>
		</button>
		<input
			:disabled="!edit"
			v-model="groupName"
			@change="group.GroupName = groupName"
			placeholder="Tag Name"
			class="form-control form-control-sm p-2 rounded-2 w-100">
		<button
			v-if="edit"
			aria-label="Delete Tag Button" @click="emits('delete')"
			class="rounded-2 border p-2 btn btn-sm btn-outline-danger">
			<i class="bi bi-trash-fill"></i>
		</button>
		<button
			v-else
			aria-label="Show / Hide Button"
			style="white-space: nowrap"
			:class="{active: !store.Filter.HiddenTags.includes(groupId)}"
			@click="toggleTag()"
			class="rounded-2  p-2 btn btn-sm btn-outline-primary">
			<i class="bi"
				:class="[!store.Filter.HiddenTags.includes(groupId) ? 'bi-eye-fill':'bi-eye-slash-fill']"
			></i>

		</button>
	</div>
</div>
</template>

<style scoped>

</style>