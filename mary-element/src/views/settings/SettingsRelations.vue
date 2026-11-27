<template>
  <GenericSettingsView
    title="Kinship & Emergency Contact Relations"
    entityName="Relation"
    apiEndpoint="/relations"
    :hasCode="true"
    :hasDescription="true"
  />
</template>

<script setup>
import GenericSettingsView from './GenericSettingsView.vue'
</script>
