<script setup>
import {computed, onMounted} from "vue";

const props = defineProps({
	message: {
		content: String,
		id: String,
		role: String,
		time: String
	},
	ind: Number
})

onMounted(() => {
	document.querySelector(".agentChatroomBody").scrollTop = 
		document.querySelector(".agentChatroomBody").scrollHeight
})

const convertMarkdown = computed(() => {
	return marked.parse(props.message.content)
})
</script>

<template>
<div :class="{'d-flex flex-row align-items-end gap-2': message.role === 'assistant', 'mt-auto': ind === 0}">
	<div class="p-2 rounded-5 text-bg-secondary" style="line-height: 1" v-if="message.role === 'assistant'">
		<i class="bi bi-robot"></i>
	</div>
	<div class="d-flex text-body agentMessage" :class="{'ms-auto': message.role === 'user'}" >
		<div class="px-3 py-2 rounded-3 shadow-sm"
		     :class="[ message.role === 'user' ? 
		        'text-bg-primary ms-auto align-items-end':'text-bg-secondary align-items-start']">
			{{ message.content }}
		</div>
	</div>
</div>
</template>

<style scoped>
.agentMessage{
	white-space: break-spaces;
	max-width: 80%;
	display: flex;
	flex-direction: column;
	word-wrap: break-word;
}

.text-bg-secondary{
	background-color: RGBA(var(--bs-secondary-rgb), 0.7) !important;
}

.text-bg-primary{
	background-color: RGBA(var(--bs-primary-rgb), 0.7) !important;
}
</style>