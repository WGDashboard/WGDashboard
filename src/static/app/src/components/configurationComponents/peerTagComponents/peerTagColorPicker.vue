<script setup lang="ts">
import {onMounted, ref} from "vue";
const props = defineProps(['colors', 'group'])
const emits = defineEmits(['close', 'select', ''])
const searchString = ref("")
import {WireguardConfigurationsStore} from "@/stores/WireguardConfigurationsStore.js"
const store = WireguardConfigurationsStore();
onMounted(() => {
	let ele = document.querySelector(".icon-grid div.active")
	if (ele){
		ele.parentElement.scrollTop =
			document.querySelector(".icon-grid div.active").offsetTop - 60
	}
})
</script>

<template>
	<div class="w-100 bg-body top-0 border rounded-2">
		<div class="p-2 d-grid icon-grid"
			 style="grid-template-columns: repeat(auto-fit, minmax(30px, 30px)); gap: 3px; max-height: 300px; overflow-y: scroll">
			<div class="rounded-1 border icon d-flex"
				 :class="{active: group.BackgroundColor === color}"
				 style="cursor: pointer"
				 :aria-label="name"
				 :style="{'background-color': color}"
				 :key="color"
				 @click="group.BackgroundColor = color"
				 v-for="(color, name) in colors">
				<i
					:style="{color: store.colorText(color)}"
					class="bi bi-check-circle m-auto" v-if="group.BackgroundColor === color"></i>
			</div>
		</div>
		<div class="p-2 border-top d-flex gap-2">
			<button class="btn btn-sm btn-success rounded-2 ms-auto" @click="emits('close')">
				Done
			</button>
		</div>
	</div>
</template>

<style scoped>
.icon{
	flex: 1;

	aspect-ratio: 1 / 1;
}
</style>