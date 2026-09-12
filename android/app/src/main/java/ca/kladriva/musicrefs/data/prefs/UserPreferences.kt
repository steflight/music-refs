package ca.kladriva.musicrefs.data.prefs

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore by preferencesDataStore(name = "music_refs_prefs")

@Singleton
class UserPreferences @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val highScoreKey = intPreferencesKey("high_score")
    private val playerNameKey = stringPreferencesKey("player_name")
    private val apiBaseKey = stringPreferencesKey("api_base_url")

    val highScoreFlow: Flow<Int> = context.dataStore.data.map { it[highScoreKey] ?: 0 }
    val playerNameFlow: Flow<String> = context.dataStore.data.map { it[playerNameKey].orEmpty() }

    suspend fun getHighScore(): Int = highScoreFlow.first()

    suspend fun saveHighScore(score: Int) {
        context.dataStore.edit { prefs ->
            val current = prefs[highScoreKey] ?: 0
            if (score > current) prefs[highScoreKey] = score
        }
    }

    suspend fun getPlayerName(): String = playerNameFlow.first()

    suspend fun savePlayerName(name: String) {
        context.dataStore.edit { it[playerNameKey] = name.trim().take(40) }
    }

    suspend fun getApiBaseOverride(): String? =
        context.dataStore.data.map { it[apiBaseKey] }.first()?.takeIf { it.isNotBlank() }

    suspend fun setApiBaseOverride(url: String?) {
        context.dataStore.edit {
            if (url.isNullOrBlank()) it.remove(apiBaseKey) else it[apiBaseKey] = url.trim().trimEnd('/')
        }
    }
}
