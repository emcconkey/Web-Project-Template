<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from '../composables/useApi'
import '../assets/styles/pages/hello.css'

const api = useApi()

const message = ref('')
const datetime = ref('')
const error = ref('')
const loading = ref(true)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const data = await api.get('/api/message')
    message.value = data.message
    datetime.value = new Date(data.datetime).toLocaleString()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="hello card">
    <h1 v-if="loading" class="hello__title">Loading…</h1>

    <template v-else-if="error">
      <h1 class="hello__title">Couldn't reach the API</h1>
      <p class="hello__error">{{ error }}</p>
      <button class="btn" @click="load">Retry</button>
    </template>

    <template v-else>
      <h1 class="hello__title">{{ message }}</h1>
      <p class="hello__time">Server time: {{ datetime }}</p>
      <button class="btn" @click="load">Refresh</button>
    </template>
  </section>
</template>
