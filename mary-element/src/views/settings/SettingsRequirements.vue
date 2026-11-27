<template>
  <GenericSettingsView
    title="Mandatory Carer Requirements"
    entityName="Requirement"
    apiEndpoint="/requirements"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
