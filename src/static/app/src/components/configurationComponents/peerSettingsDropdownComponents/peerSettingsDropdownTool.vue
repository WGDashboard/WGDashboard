<script setup>
import {ref} from "vue";
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps({
	icon: String,
	title: String
})
const emit = defineEmits(["click"])

const show = ref(false)

</script>

<template>
	<a class="dropdown-item text-center px-0 rounded-3 position-relative" role="button"
	   :aria-label="title"
	   @mouseenter="show = true"
	   @mouseleave="show = false"
	   @click="emit('click')">
		<i class="me-auto bi" :class="icon" aria-hidden="true"></i>
		<Transition name="zoomReversed">
			<span
				v-if="show"
				class="position-absolute d-block p-1 px-2 bg-body text-body rounded-3 border shadow">
			<small>
				<LocaleText :t="title"></LocaleText>
			</small>
		</span>
		</Transition>
	</a>
</template>

<style scoped>
span{
	top: -34px;
	left: 0;
}
</style>
