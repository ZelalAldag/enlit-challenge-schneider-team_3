import streamlit as st
import textwrap

# Define colors
SCHNEIDER_GREEN = "#009E06"
SCHNEIDER_GRAY = "#3D3D3D"
LIGHT_GRAY = "#F4F4F4"


def render_chatbot():
    """
    Renders the chatbot UI.
    Uses textwrap.dedent to strictly remove Python indentation
    so Streamlit renders HTML instead of a code block.
    """

    st.markdown("#### 🤖 AI Assistant")

    # HTML content
    # We use textwrap.dedent(f"""...""") to strip the whitespace
    html_code = textwrap.dedent(
        f"""
        <div style='background-color: {LIGHT_GRAY}; padding: 15px; border-radius: 10px; border: 2px solid {SCHNEIDER_GREEN}; height: 450px; overflow-y: auto; font-family: sans-serif;'>
            
            <!-- Header -->
            <div style='border-bottom: 1px solid #ddd; margin-bottom: 15px; padding-bottom: 5px; position: sticky; top: 0; background-color: {LIGHT_GRAY}; z-index: 10;'>
                <h4 style='color: {SCHNEIDER_GREEN}; margin: 0;'>Energy Optimization Bot</h4>
                <small style='color: {SCHNEIDER_GRAY};'>Online | Connected to Site Data</small>
            </div>

            <!-- Chat Container -->
            <div style='display: flex; flex-direction: column; gap: 15px;'>

                <!-- User Message 1 -->
                <div style='display: flex; justify-content: flex-end; align-items: flex-end;'>
                    <div style='background-color: {SCHNEIDER_GREEN}; color: white; padding: 12px 15px; border-radius: 15px 15px 0 15px; max-width: 80%; font-size: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.1);'>
                        I see a critical alert on Chiller 2. What is causing the variance?
                    </div>
                    <span style='font-size: 20px; margin-left: 5px;'>👤</span>
                </div>

                <!-- AI Message 1 -->
                <div style='display: flex; justify-content: flex-start; align-items: flex-start;'>
                    <span style='font-size: 20px; margin-right: 5px;'>⚡</span>
                    <div style='background-color: white; color: {SCHNEIDER_GRAY}; padding: 15px; border-radius: 15px 15px 15px 0; max-width: 90%; font-size: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); border: 1px solid #e0e0e0;'>
                        <strong>Analysis Report</strong><br>
                        I've analyzed the real-time data. Chiller 2 is consuming <strong>15% more energy</strong> than expected.<br><br>
                        <span style='text-decoration: underline;'>Diagnosis:</span> COP dropped from 3.2 to 2.7. This indicates a potential <strong>stuck expansion valve</strong>.
                    </div>
                </div>

                <!-- User Message 2 -->
                <div style='display: flex; justify-content: flex-end; align-items: flex-end;'>
                    <div style='background-color: {SCHNEIDER_GREEN}; color: white; padding: 12px 15px; border-radius: 15px 15px 0 15px; max-width: 80%; font-size: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.1);'>
                        How much will I save if I shift Polishing to P6?
                    </div>
                    <span style='font-size: 20px; margin-left: 5px;'>👤</span>
                </div>

                <!-- AI Message 2 -->
                <div style='display: flex; justify-content: flex-start; align-items: flex-start;'>
                    <span style='font-size: 20px; margin-right: 5px;'>⚡</span>
                    <div style='background-color: white; color: {SCHNEIDER_GRAY}; padding: 15px; border-radius: 15px 15px 15px 0; max-width: 90%; font-size: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); border: 1px solid #e0e0e0;'>
                        <strong>Optimization Result</strong><br>
                        Shifting 'Polishing' to P6 (22:00-06:00) targets the lowest tariff (€0.61/kW).<br><br>
                        <div style='background-color: #e8f5e9; padding: 10px; border-radius: 5px; border-left: 4px solid {SCHNEIDER_GREEN}; margin-top: 5px;'>
                            <strong>💰 Projected Savings: €5,200 / year</strong><br>
                            <small>ROI: Immediate (0 Investment)</small>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    """
    )

    # Render the HTML
    st.html(html_code)

    # Chat Input
    st.text_input(
        "Ask the AI Consultant:",
        placeholder="Type your question here...",
        key="ai_chat_visual_input_fixed",
    )
