<script setup lang="ts">
import {computed, onMounted, ref} from "vue";
const props = defineProps(['group'])
import bootstrapIcons from "bootstrap-icons/font/bootstrap-icons.json"
const emits = defineEmits(['close', 'select'])
onMounted(() => {
	let ele = document.querySelector(".icon-grid div.active")
	if (ele){
		ele.parentElement.scrollTop =
			document.querySelector(".icon-grid div.active").offsetTop - 60
	}
})
const searchString = ref("")
const searchIcon = computed(() => {
	if (searchString.value){

		return [...Object.keys(bootstrapIcons).filter(
			x => x.includes(searchString.value.toLowerCase())
		)]
	}
	return Object.keys(bootstrapIcons)
})
</script>

<template>
<div class="w-100 bg-body top-0 border rounded-2">
	<div class="p-2 d-flex align-items-center gap-2 border-bottom">
		<label>
			<i class="bi bi-search"></i>
		</label>
		<input v-model="searchString"
			   placeholder="Search Icon"
			   class="form-control form-control-sm rounded-2">
	</div>
	<div class="p-2 d-grid icon-grid"
		 style="grid-template-columns: repeat(auto-fit, minmax(30px, 30px)); gap: 3px; max-height: 300px; overflow-y: scroll">
		<div class="rounded-1 border icon d-flex"
			 :class="{'text-bg-success active' : group.Icon === iconName}"
			 style="cursor: pointer"
			 :key="iconName"
			 @click="group.Icon = iconName"
			 v-for="iconName in searchIcon">
			<i class="bi m-auto" :class="'bi-' + iconName"></i>
		</div>
	</div>
	<div class="p-2 border-top d-flex gap-2">
		<button
			@click="group.Icon = ''"
			class="btn btn-sm btn-secondary rounded-2 ms-auto">
			Remove Icon
		</button>
		<button class="btn btn-sm btn-success rounded-2" @click="emits('close')">
			Done
		</button>
	</div>
</div>
</template>

<style scoped>
.icon{
	flex: 1;
	min-width: 30px;
	max-width: 30px;
	width: 30px;
	aspect-ratio: 1 / 1;
}
</style>