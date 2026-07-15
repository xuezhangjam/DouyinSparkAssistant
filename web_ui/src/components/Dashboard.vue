<template>
  <div class="dashboard">
    <div class="d-flex align-center mb-6 gap-4">
      <v-btn color="primary" variant="elevated" prepend-icon="mdi-play-circle" @click="runAll" rounded="pill" class="text-none">
        批量自动续火花
      </v-btn>
      <v-btn color="secondary" variant="tonal" prepend-icon="mdi-plus" @click="addClientDialog = true" rounded="pill" class="text-none">
        添加新客户
      </v-btn>
    </div>

    <v-card elevation="2" rounded="xl" class="overflow-hidden border" color="surface">
      <v-data-table
        :headers="headers"
        :items="clients"
        :items-per-page="10"
        hover
      >
        <template v-slot:item.actions="{ item }">
          <v-btn size="small" color="primary" variant="tonal" class="mr-2" @click="runSingle(item)" rounded="pill">
            运行
          </v-btn>
          <v-btn size="small" color="error" variant="tonal" @click="confirmDelete(item)" rounded="pill">
            删除
          </v-btn>
        </template>
      </v-data-table>
    </v-card>

    <!-- 添加客户对话框 -->
    <v-dialog v-model="addClientDialog" max-width="400" persistent>
      <v-card rounded="xl">
        <v-card-title class="pt-4 px-6 font-weight-bold">添加客户</v-card-title>
        <v-card-text class="px-6 pb-2">
          <v-text-field
            v-model="newClientId"
            label="请输入客户编号(纯数字)"
            variant="outlined"
            color="primary"
            autofocus
            @keyup.enter="submitAddClient"
          ></v-text-field>
        </v-card-text>
        <v-card-actions class="px-6 pb-4">
          <v-spacer></v-spacer>
          <v-btn color="secondary" variant="text" @click="addClientDialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" rounded="pill" @click="submitAddClient">确定</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 删除确认对话框 -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card rounded="xl">
        <v-card-title class="pt-4 px-6 text-error font-weight-bold">警告</v-card-title>
        <v-card-text class="px-6 py-2">
          确定要删除客户 <strong class="text-primary">{{ itemToDelete?.id }}</strong> 吗？
        </v-card-text>
        <v-card-actions class="px-6 pb-4">
          <v-spacer></v-spacer>
          <v-btn color="secondary" variant="text" @click="deleteDialog = false">取消</v-btn>
          <v-btn color="error" variant="flat" rounded="pill" @click="deleteClient">确定删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- 提示框 Snackbar -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000" rounded="pill">
      {{ snackbar.text }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const clients = ref<any[]>([])
const addClientDialog = ref(false)
const newClientId = ref('')
const deleteDialog = ref(false)
const itemToDelete = ref<any>(null)

const snackbar = ref({
  show: false,
  text: '',
  color: 'success'
})

const showMsg = (text: string, color: string = 'success') => {
  snackbar.value = { show: true, text, color }
}

const headers = [
  { title: '客户编号', key: 'id', align: 'start' as const },
  { title: '备注名称', key: 'alias' },
  { title: '火花数量', key: 'friends_count' },
  { title: '操作', key: 'actions', align: 'center' as const, sortable: false },
]

const fetchClients = async () => {
  try {
    const res = await axios.get('/api/clients')
    clients.value = Object.keys(res.data).map(key => ({
      id: key,
      ...res.data[key]
    }))
  } catch (e) {
    showMsg('无法获取客户数据', 'error')
  }
}

const submitAddClient = async () => {
  if (!newClientId.value) return
  const current: any = {}
  clients.value.forEach(c => { 
    const { id, ...rest } = c;
    current[c.id] = rest;
  })
  current[newClientId.value] = { alias: "新客户", friends_count: 5, user_data_dir: `user_data_${newClientId.value}` }
  
  try {
    await axios.post('/api/clients', current)
    showMsg('添加成功')
    addClientDialog.value = false
    newClientId.value = ''
    fetchClients()
  } catch (e) {
    showMsg('添加失败', 'error')
  }
}

const confirmDelete = (item: any) => {
  itemToDelete.value = item
  deleteDialog.value = true
}

const deleteClient = async () => {
  if (!itemToDelete.value) return
  const current: any = {}
  clients.value.forEach(c => { 
    if (c.id !== itemToDelete.value.id) {
      const { id, ...rest } = c;
      current[c.id] = rest;
    }
  })
  try {
    await axios.post('/api/clients', current)
    showMsg('删除成功')
    deleteDialog.value = false
    itemToDelete.value = null
    fetchClients()
  } catch(e) {
    showMsg('删除失败', 'error')
  }
}

const runAll = async () => {
  try {
    await axios.post('/api/run', {})
    showMsg('任务已在后台启动！')
  } catch (e) {
    showMsg('启动失败', 'error')
  }
}

const runSingle = async (row: any) => {
  try {
    await axios.post('/api/run', { cid: row.id })
    showMsg(`开始处理客户: ${row.id}`)
  } catch (e) {
    showMsg('启动失败', 'error')
  }
}

onMounted(() => {
  fetchClients()
})
</script>

<style scoped>
.gap-4 {
  gap: 16px;
}
</style>
