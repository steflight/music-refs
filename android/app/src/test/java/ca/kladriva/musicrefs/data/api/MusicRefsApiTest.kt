package ca.kladriva.musicrefs.data.api

import ca.kladriva.musicrefs.data.model.PartyCreateRequest
import com.google.common.truth.Truth.assertThat
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Before
import org.junit.Test
import retrofit2.Retrofit

class MusicRefsApiTest {
    private lateinit var server: MockWebServer
    private lateinit var api: MusicRefsApi

    private val json = Json { ignoreUnknownKeys = true }

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        api = Retrofit.Builder()
            .baseUrl(server.url("/"))
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(MusicRefsApi::class.java)
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun categories_parsesList() = runBlocking {
        server.enqueue(
            MockResponse().setBody(
                """[{"id":7,"slug":"mbole","name":"Mbole","description":"","quote_count":18}]""",
            ),
        )
        val cats = api.categories()
        assertThat(cats).hasSize(1)
        assertThat(cats.first().name).isEqualTo("Mbole")
        assertThat(server.takeRequest().path).isEqualTo("/api/music-refs/categories")
    }

    @Test
    fun createParty_sendsEasyMode() = runBlocking {
        server.enqueue(
            MockResponse().setBody(
                """
                {
                  "id":1,"code":"ABCDEF","status":"lobby","round_limit":8,"mode":"easy",
                  "category":{"id":7,"slug":"mbole","name":"Mbole","quote_count":18},
                  "players":[{"id":1,"name":"Steph","is_host":true,"score":0,"finished":false,"progress":0,"total":8}],
                  "me":{"id":1,"name":"Steph","is_host":true,"score":0,"finished":false,"progress":0,"total":8,
                        "player_token":"p","host_token":"h"},
                  "quote_count":0
                }
                """.trimIndent(),
            ),
        )
        val snap = api.createParty(
            PartyCreateRequest(categoryId = 7, hostName = "Steph", roundLimit = 8, mode = "easy"),
        )
        assertThat(snap.mode).isEqualTo("easy")
        assertThat(snap.code).isEqualTo("ABCDEF")
        val req = server.takeRequest()
        assertThat(req.path).isEqualTo("/api/music-refs/parties")
        assertThat(req.body.readUtf8()).contains("\"mode\":\"easy\"")
    }
}
