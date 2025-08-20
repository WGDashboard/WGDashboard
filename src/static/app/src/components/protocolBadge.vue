<script setup>
import LocaleText from "@/components/text/localeText.vue";
import {onMounted, ref} from "vue";

const props = defineProps({
	protocol: String,
	mini: false
})
</script>

<template>
<div class="position-relative">
	<span class="badge wireguardBg rounded-3 shadow z-1"
		  v-if="protocol === 'wg'">
		WireGuard <LocaleText t="Configuration" v-if="!mini"></LocaleText>
	</span>
	<span class="badge amneziawgBg rounded-3 shadow"
		  v-else-if="protocol === 'awg'">
		AmneziaWG <LocaleText t="Configuration" v-if="!mini"></LocaleText>
	</span>
</div>
</template>

<style scoped>
</style>