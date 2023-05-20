module slice_decoder(
	// lms load interface for decoder, lms_state goes in here
	input wire lms_load,
	input wire signed [15:0] lms_load_history[0:3],
	input wire signed [15:0] lms_load_weights[0:3],

	// slice input interface
	input wire load_slice,
	input wire[63:0] new_slice_data,
	output wire slice_empty, // if set next clk must do a new load_slice

	// sample data output
	output wire signed [31:0] sample,

	input wire clk, // sample clock
	input wire rst,

	// allow a view into the internal lms state for the encoder to save them
	output reg signed [15:0] lms_save_history[0:3],
	output reg signed [15:0] lms_save_weights[0:3]
);
reg[63:0] slice_data;

always @ * begin

end

always @ (posedge clk) begin
	if (load_slice) begin

	end

	if (rst) begin

	end
end

endmodule
