<template>
  <GenericSettingsView
    title="Care Types Classification"
    entityName="Care Type"
    apiEndpoint="/care-types"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
