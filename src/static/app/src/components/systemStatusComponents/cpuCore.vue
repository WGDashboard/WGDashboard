<script setup>
import {computed, ref} from "vue";
import LocaleText from "@/components/text/localeText.vue";

const props = defineProps({
	core_number: Number,
	percentage: Number,
	align: Boolean,
	square: Boolean
})
const show = ref(false)

const squareHeight = computed(() => {
	return props.square ? "40px": "25px"
})



</script>

<template>
	<div class="flex-grow-1 square rounded-3 border position-relative p-2"
	     
	     @mouseenter="show = true"
	     @mouseleave="show = false"
	     :style="{'background-color': `rgb(13 110 253 / ${percentage*10}%)`}">
		<Transition name="zoomReversed">
			<div
				v-if="show"
				style="white-space: nowrap;"
				:style="{'top': squareHeight}"
				class="floatingLabel z-3 border position-absolute d-block p-1 px-2 
				bg-body text-body rounded-3 border shadow d-flex"
				:class="[align ? 'end-0':'start-0']"
			>
				<small class="text-muted me-2">
					<LocaleText t="Core"></LocaleText> #{{core_number + 1}}
				</small>
				<small class="fw-bold">
					{{percentage}}%
				</small>
			</div>
		</Transition>
	</div>
</template>

<style scoped>
.square{
	height: v-bind(squareHeight);
	transition: background-color 0.5s cubic-bezier(0.42, 0, 0.22, 1.0);
}

</style>